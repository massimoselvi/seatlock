# 0003. Target AWS architecture

Status: Accepted

## Context

Seatlock runs on Docker Compose today: Django (gunicorn), a Celery worker, PostgreSQL, Redis and a Vue single-page app.
We need a production target that is cheap to run for a small workload, safe for the seat-locking rules, and easy to explain.

Constraints from earlier decisions:

- Seat allocation uses Postgres row locks ([ADR 0001](0001-row-locks-for-seat-allocation.md)). The database must be a real PostgreSQL, reached through direct connections or a pooler in session mode.
- Tasks are enqueued on commit ([ADR 0002](0002-enqueue-celery-tasks-on-commit.md)). The broker is Redis.
- The code also uses Redis as the cache and for throttle counters.

## Decision

Run in one region (`eu-west-1`) with managed services and no servers to patch.

```mermaid
flowchart LR
    user([Browser]) --> cf[CloudFront]
    cf -->|static files| s3[(S3: Vue build)]
    cf -->|/api/*| alb[Application Load Balancer]
    alb --> web[ECS Fargate: web<br/>gunicorn, 2 tasks]
    web --> rds[(RDS PostgreSQL)]
    web --> redis[(ElastiCache Redis)]
    worker[ECS Fargate: worker<br/>Celery, 1 task] --> redis
    worker --> rds
    worker --> ses[SES: email]
    web -. logs, metrics .-> cw[CloudWatch]
    worker -. logs, metrics .-> cw
```

| Part | Choice | Why |
|------|--------|-----|
| Compute | ECS on Fargate, one service for `web`, one for `worker` | Same container image as Compose. No hosts to manage. |
| Database | RDS PostgreSQL 17, Multi-AZ in production | Row locks need real Postgres. Automated backups and failover. |
| Cache and broker | ElastiCache for Redis | The code already speaks Redis. No application change. |
| Entry | CloudFront in front of an ALB, with the SPA in S3 | One domain, TLS, caching of static files. `/api/*` goes to the ALB. |
| Email | SES | Waitlist promotion emails. |
| Secrets | Secrets Manager, injected as task secrets | Nothing sensitive in the image or in environment files. |
| Logs and alarms | CloudWatch | Alarms from [the SLO document](../slo.md). |
| Network | One VPC, tasks and data in private subnets | Only the ALB is public. |

## Alternatives

- **Lambda with API Gateway.** It scales to zero, but database connections and long-lived Celery workers fit badly. Connection limits on RDS need a proxy.
- **App Runner.** Simpler than ECS, but it has no worker service and little network control.
- **EKS.** Too much to run for one small application.
- **SQS instead of Redis for Celery.** SQS is more durable, but it needs a broker change and does not replace the cache. We keep Redis for now. If we need stronger delivery, add a periodic sweep first (see ADR 0002), then reconsider SQS.
- **EC2 with Docker Compose.** Cheapest on paper, but we own patching, backups and failover.

## Consequences

- The application needs no code change to deploy, only configuration (`DATABASE_URL`, `CELERY_BROKER_URL`, `CACHE_URL`).
- Redis is a single point of failure for throttling, cache and tasks. Throttle and cache errors must not break reads. A replica gives failover.
- Fargate tasks in private subnets need a NAT gateway or VPC endpoints to reach ECR, Secrets Manager and SES. NAT is the largest fixed cost after compute.

## Failure modes

| Failure | Effect | Mitigation |
|---------|--------|------------|
| One web task dies | Capacity drops | ALB health check, ECS replaces it, minimum 2 tasks |
| Worker down | Waitlist not promoted | Queue backlog alarm, restart. See the [runbook](../runbooks/queue-backlog.md). |
| Database failover | About 1 to 2 minutes of errors | Multi-AZ, retry on the client |
| Redis down | Cache and throttle fail, tasks wait | Replica, graceful fallback on cache errors |
| Bad deploy | Errors rise | Rolling deploy with circuit breaker, rollback to the previous task definition |

## Estimated monthly cost

Rough list prices for `eu-west-1`, on demand, USD. These are estimates for planning. Check them with the AWS Pricing Calculator before committing.

| Item | Demo (single AZ) | Production-like |
|------|------------------|-----------------|
| Fargate: 2 web tasks (0.5 vCPU, 1 GB) + 1 worker (0.25 vCPU, 0.5 GB) | 45 | 45 |
| RDS PostgreSQL `db.t4g.micro`, 20 GB | 15 | 30 (Multi-AZ) |
| ElastiCache `cache.t4g.micro` | 12 | 24 (with replica) |
| Application Load Balancer | 20 | 20 |
| NAT gateway | 0 (tasks in public subnets) | 35 |
| CloudFront, S3, ECR, Secrets Manager | 5 | 5 |
| CloudWatch logs and alarms | 5 | 10 |
| **Total** | **about 100** | **about 170** |

The demo column trades safety for cost: tasks sit in public subnets with tight security groups and the database is single AZ.
Do not run the demo setup with real user data.
