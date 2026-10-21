# 0004. Infrastructure as code with AWS CDK

Status: Accepted

## Context

[ADR 0003](0003-target-aws-architecture.md) defines the AWS target.
We need to create it the same way every time, review changes in pull requests, and check them in CI without an AWS account.

## Decision

Define the infrastructure with the AWS CDK in Python, in `infra/`.

- Use Python, the language of the application, and `uv` for dependencies.
- Split the app into stacks by how often they change and how risky they are:
  - `NetworkStack`: VPC, subnets, security groups.
  - `DataStack`: RDS, ElastiCache, secrets. Deletion protection on.
  - `AppStack`: ECR, ECS services, ALB, alarms.
  - `FrontendStack`: S3 bucket and CloudFront.
- Keep environment settings (sizes, Multi-AZ, domain) in one config object, so demo and production differ by values, not by code.
- CI runs `cdk synth` on every pull request. A synth error fails the build. It needs no AWS credentials.
- Deploy from a manual, approved workflow that assumes an AWS role through GitHub OIDC. Never store long-lived keys.

## Alternatives

- **Terraform.** Wide ecosystem and a clear plan output, but it adds a second language and a state backend to run.
- **Plain CloudFormation.** Verbose. No loops, no functions, no unit tests.
- **Pulumi.** Similar to CDK, but with a smaller AWS community and a hosted state service by default.
- **Click-ops.** Fast once, impossible to review or repeat.

## Consequences

- Infrastructure changes are code reviews, with the same branch rules as the application.
- `cdk synth` catches wiring mistakes early, but it does not prove the stack deploys. Quotas, IAM limits and naming clashes appear only at deploy time.
- The CDK version is pinned in `uv.lock`. Upgrades are their own pull request.
- Stateful resources (RDS, S3 data) use a retain policy. A stack delete never removes data by accident.
