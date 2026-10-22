# Deploy and rollback

How to ship Seatlock to AWS and how to undo a release.
Architecture: [ADR 0003](architecture/adr/0003-target-aws-architecture.md). Infrastructure code: [infra/](../infra/README.md).

> Nothing in this guide has been run against a real AWS account yet. Treat the first deploy as a dry run in a throwaway account and fix the guide with what you learn.
> A one-day demo run costs about 3 ([cost analysis](cost-analysis.md)). Destroy it afterwards.

## Prerequisites

- AWS CLI v2 with credentials for the target account, region `eu-west-1`.
- Docker with `buildx`, `jq`, Node 22, and `uv`.
- CDK bootstrapped once per account and region: `npx aws-cdk@2.1146.0 bootstrap aws://<account>/eu-west-1`.
- The pinned CloudFront prefix list is right for the region. This must print the same ID as `CLOUDFRONT_ORIGIN_PREFIX_LISTS` in `infra/seatlock_infra/network_stack.py`:

  ```bash
  aws ec2 describe-managed-prefix-lists --region eu-west-1 \
    --filters Name=prefix-list-name,Values=com.amazonaws.global.cloudfront.origin-facing \
    --query "PrefixLists[0].PrefixListId" --output text
  ```

Helper used below. It reads a stack output:

```bash
out() { aws cloudformation describe-stacks --stack-name "$1" \
  --query "Stacks[0].Outputs[?OutputKey=='$2'].OutputValue" --output text; }
ENVNAME=demo   # or prod
```

## First deploy

The ECS services need an image in ECR. The `bootstrap` flag creates every resource with zero running tasks, so the first deploy does not fail on a missing image.

```bash
cd infra && uv sync
npx aws-cdk@2.1146.0 deploy --all -c env=$ENVNAME -c bootstrap=true -c alarm_email=you@example.com \
  -c destroy_by=2026-12-31   # optional: a DestroyBy tag on every resource
```

The load balancer accepts traffic only from CloudFront. Use the CloudFront URL (`SiteUrl`) for every request, including smoke tests and load tests.

Then ship a release (next section) and finish with a normal deploy, without `bootstrap`, to start the tasks.

## Ship a release

Every release has five steps, in this order. Steps 3 and 4 run the new code, so migrations must be backward compatible (see below).

```bash
TAG=$(git rev-parse --short HEAD)
REPO=$(out Seatlock-$ENVNAME-App RepositoryUri)
```

**1. Build and push the image.** Build for `linux/amd64`: Fargate tasks here run on x86.

```bash
aws ecr get-login-password --region eu-west-1 | docker login --username AWS --password-stdin "${REPO%%/*}"
docker buildx build --platform linux/amd64 -t "$REPO:$TAG" --push backend
```

**2. Run migrations once, as a one-off task.** Tasks do not migrate on start, so parallel tasks cannot race.
This registers a copy of the web task definition that points at the new image, then runs it.

```bash
CLUSTER=$(out Seatlock-$ENVNAME-App ClusterName)
FAMILY=$(out Seatlock-$ENVNAME-App WebTaskFamily)
SG=$(out Seatlock-$ENVNAME-Network AppSecurityGroupId)
SUBNETS=$(out Seatlock-$ENVNAME-Network TaskSubnetIds)
PUBLIC_IP=ENABLED   # prod uses private subnets: DISABLED

NEW_TD=$(aws ecs describe-task-definition --task-definition "$FAMILY" --query taskDefinition \
  | jq --arg img "$REPO:$TAG" \
    'del(.taskDefinitionArn,.revision,.status,.requiresAttributes,.compatibilities,.registeredAt,.registeredBy)
     | .containerDefinitions[0].image = $img')
TD_ARN=$(aws ecs register-task-definition --cli-input-json "$NEW_TD" \
  --query taskDefinition.taskDefinitionArn --output text)

TASK=$(aws ecs run-task --cluster "$CLUSTER" --launch-type FARGATE --task-definition "$TD_ARN" \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNETS],securityGroups=[$SG],assignPublicIp=$PUBLIC_IP}" \
  --overrides '{"containerOverrides":[{"name":"web","command":["sh","-c","export DATABASE_URL=postgres://$DB_USER:$DB_PASSWORD@$DB_HOST:5432/$DB_NAME && python manage.py migrate --noinput"]}]}' \
  --query 'tasks[0].taskArn' --output text)

aws ecs wait tasks-stopped --cluster "$CLUSTER" --tasks "$TASK"
aws ecs describe-tasks --cluster "$CLUSTER" --tasks "$TASK" \
  --query 'tasks[0].containers[0].exitCode'      # must print 0
```

If the exit code is not 0, stop. Read the task log in CloudWatch. Nothing has changed for users yet.

**3. Deploy the new image.** ECS replaces tasks one by one. The circuit breaker rolls back by itself if new tasks fail their health check.

```bash
cd infra
npx aws-cdk@2.1146.0 deploy --all -c env=$ENVNAME -c image_tag=$TAG
```

**4. Publish the frontend.**

```bash
cd ../frontend && pnpm install --frozen-lockfile && pnpm build
BUCKET=$(out Seatlock-$ENVNAME-Frontend BucketName)
DIST=$(out Seatlock-$ENVNAME-Frontend DistributionId)
aws s3 sync dist "s3://$BUCKET" --delete
aws cloudfront create-invalidation --distribution-id "$DIST" --paths "/*"
```

**5. Smoke test.**

```bash
SITE=$(out Seatlock-$ENVNAME-Frontend SiteUrl)
curl -fsS "$SITE/api/health/"          # {"status": "ok"}
curl -fsS "$SITE/api/workshops/" | head -c 200
```

Then watch the dashboards and alarms for 15 minutes.

## Migration rule: expand, then contract

Old and new code run side by side during a deploy, and rollback runs old code on the new schema. So:

- **Expand release:** add columns and tables as nullable or with defaults. Never rename or drop in the same release.
- **Contract release:** drop or rename only after no running code reads the old shape.
- Any change to seat-count logic keeps `select_for_update()` inside `transaction.atomic` ([ADR 0001](architecture/adr/0001-row-locks-for-seat-allocation.md)).

## Rollback

### Triggers

Roll back first and investigate second when any of these holds after a release:

| Signal | Threshold | Source |
|--------|-----------|--------|
| 5xx rate | above 2% for 5 minutes | `HighErrorRate` alarm |
| Latency | p95 above 800 ms for 10 minutes | `SlowRequests` alarm |
| Unhealthy web tasks | any, for 3 minutes | `UnhealthyWebTasks` alarm |
| Deployment | circuit breaker triggered | ECS service events |
| Seats | any workshop over capacity | [runbook](runbooks/seats-oversold.md). Stop registrations first. |
| Smoke test | health or workshops call fails | release step 5 |

### Application

Redeploy the previous image tag. Find it in ECR or in `git log`.

```bash
cd infra
npx aws-cdk@2.1146.0 deploy --all -c env=$ENVNAME -c image_tag=<previous-tag>
```

This is a rolling deploy with the same circuit breaker. It needs no database change, thanks to the migration rule above.

Faster, without CDK: point the service at the previous task definition revision.

```bash
aws ecs update-service --cluster "$CLUSTER" --service "$(out Seatlock-$ENVNAME-App WebServiceName)" \
  --task-definition "$FAMILY:<previous-revision>"
```

Run the same for the worker service. Redeploy through CDK afterwards so the code and the stack agree again.

### Frontend

Check out the previous release, rebuild, and repeat step 4. The bucket is not versioned.

### Database

Do not roll the schema back. Ship a corrective migration as a new release.
For corrupted data, restore a point in time to a **new** instance, check it, then switch the `DB_HOST` value. Never restore over the live instance.

```bash
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier <current> --target-db-instance-identifier <restored> \
  --restore-time 2026-01-01T10:00:00Z
```

## Operations

- **Logs:** CloudWatch log groups for `web` and `worker`, kept for one month.
- **Alarms:** email goes to the address passed as `alarm_email`. Confirm the SNS subscription once.
- **Shell access:** use `aws ecs run-task` with a command override, as in step 2. Do not open ports to the database.
- **Staff users:** run `python manage.py shell` as a one-off task and set `is_staff=True`, then use the organizer dashboard.
- **Cost control (demo):** the demo costs about 0.12 to 0.16 an hour while it exists. Destroy it between sessions. Scaling tasks to zero saves only about 56 of the 113 a month. See the [cost analysis](cost-analysis.md).
- **Budget:** create an AWS Budgets alarm at 200 a month before the first deploy.

```bash
aws ecs update-service --cluster "$CLUSTER" --service "$(out Seatlock-$ENVNAME-App WebServiceName)" --desired-count 0
npx aws-cdk@2.1146.0 destroy --all -c env=demo   # deletes the demo database too
```

`prod` keeps its data on destroy (retain policy and deletion protection). Remove it by hand on purpose.

## Known gaps

See [infra/README.md](../infra/README.md): HTTP between CloudFront and the ALB, and two alarms from [slo.md](slo.md) with no metric source yet.
