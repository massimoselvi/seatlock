# Infrastructure

AWS CDK (Python) for the architecture in [ADR 0003](../docs/architecture/adr/0003-target-aws-architecture.md).
Why CDK: [ADR 0004](../docs/architecture/adr/0004-infrastructure-as-code-with-aws-cdk.md).

| Stack | Holds |
|-------|-------|
| `Network` | VPC, subnets, security groups |
| `Data` | PostgreSQL, Redis, secrets |
| `App` | ECR, ECS web and worker, ALB, alarms |
| `Frontend` | S3 bucket, CloudFront |

## Commands

```bash
cd infra
uv sync
uv run pytest                                   # assertions on the generated templates
npx aws-cdk@2.1146.0 synth                      # demo environment, no AWS account needed
npx aws-cdk@2.1146.0 synth -c env=prod          # production-like
npx aws-cdk@2.1146.0 diff -c env=prod           # needs AWS credentials
```

Options (`-c key=value`): `env` (`demo` or `prod`), `alarm_email`, `image_tag`, `destroy_by` (a date, added as the `DestroyBy` tag).
Every resource gets the tags `Project=seatlock`, `Env` and `ManagedBy=cdk`. List everything the project owns with the Resource Groups Tagging API, or filter Cost Explorer by `Project`.
Demo and prod differ only in `seatlock_infra/config.py`.

## Known limits

- The ALB accepts traffic only from CloudFront, through the AWS-managed prefix list `com.amazonaws.global.cloudfront.origin-facing`. Its ID is pinned per region in `network_stack.py`, because it cannot be looked up without an account. Check it before a deploy, and add the region to the table if you change region. The ALB DNS name is not reachable from anywhere else, so use the CloudFront URL for smoke tests and load tests.
- CloudFront still reaches the ALB over HTTP. Add TLS before real traffic.
- The queue backlog alarm from [docs/slo.md](../docs/slo.md) is missing. Celery's queue length is not a CloudWatch metric, so it needs a small publisher.
- The "oversold workshop" alarm needs a scheduled check against the database. Also missing.
