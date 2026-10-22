## Decisions

The decisions that shape this architecture are written as ADRs in the repository, in `docs/adr/`. The list below is kept by hand. Update it when an ADR is added or its status changes.

| ADR | Decision | Status | Shown in |
|-----|----------|--------|----------|
| [0001](https://github.com/massimoselvi/seatlock/blob/main/docs/adr/0001-row-locks-for-seat-allocation.md) | Use row locks (`SELECT ... FOR UPDATE`) for seat allocation. | Accepted | flow-register |
| [0002](https://github.com/massimoselvi/seatlock/blob/main/docs/adr/0002-enqueue-celery-tasks-on-commit.md) | Enqueue Celery tasks on commit. | Accepted | flow-cancel-promote |
| [0003](https://github.com/massimoselvi/seatlock/blob/main/docs/adr/0003-target-aws-architecture.md) | Target AWS architecture: ECS Fargate, RDS, ElastiCache, CloudFront, S3. | Accepted | deploy-aws-demo, deploy-aws-prod |
| [0004](https://github.com/massimoselvi/seatlock/blob/main/docs/adr/0004-infrastructure-as-code-with-aws-cdk.md) | Infrastructure as code with AWS CDK in Python. | Accepted | deploy-aws-demo, deploy-aws-prod |
| [0005](https://github.com/massimoselvi/seatlock/blob/main/docs/adr/0005-clean-architecture-experiment.md) | Clean Architecture for the backend: four layers, a unit-of-work port, one composition root. | Accepted | api-components, api-ports-adapters |
| [0006](https://github.com/massimoselvi/seatlock/blob/main/docs/adr/0006-style-the-frontend-with-unocss.md) | Style the frontend with UnoCSS and the antfu toolchain. | Accepted | spa-components |
