# Cost analysis

Monthly cost of the architecture in [ADR 0003](adr/0003-target-aws-architecture.md), in USD, region `eu-west-1`.

- **Prices:** on demand, from the AWS Price List Bulk API, publication 2026-10-20.
- **Model:** [cost/model.py](cost/model.py). Standard library only. Run `python3 docs/cost/model.py` to reproduce every number here.
- **Status:** prices are sourced. Traffic is assumed, because the app has no users yet. Treat totals as plus or minus 10% until real traffic exists.

## Answer

| Setup | Low traffic | Expected | High |
|-------|-------------|----------|------|
| **Demo**: 1 AZ, no NAT, 2 web + 1 worker | 113 | 116 | 177 |
| **Demo lean**: 1 web + 1 worker, ARM | 86 | 89 | 150 |
| **Production-like**: Multi-AZ, NAT, Redis replica | 169 | 172 | 234 |
| **Production-like on ARM** | 160 | 163 | 225 |

WAF ([#59](https://github.com/massimoselvi/seatlock/issues/59)) adds about 9 (low), 10 (expected) or 33 (high) a month.

**Cost is almost all fixed.** At expected traffic, more than 95% of the bill is for resources that run whether or not anyone visits. Traffic starts to matter above 10 million requests a month, when CloudFront leaves its free tier. The high case (40 million requests) adds about 65 a month.

## Assumptions

| | Low | Expected | High |
|---|-----|----------|------|
| Requests per month | 50 thousand | 2 million | 40 million (about 15 per second) |
| Response data | 1 GB | 10 GB | 400 GB |
| Log data | 0.5 GB | 2 GB | 20 GB |
| Emails sent | 100 | 2 thousand | 40 thousand |
| ALB capacity units, average | 0.1 | 0.5 | 2 |

Sizes: web task 0.5 vCPU and 1 GB, worker task 0.25 vCPU and 0.5 GB, `db.t4g.micro` with 20 GB gp3, `cache.t4g.micro`. A month is 730 hours.

## Where the money goes

| Item | Demo, low traffic | Production-like, expected |
|------|------------------:|--------------------------:|
| Fargate (web and worker) | 45.05 | 45.05 |
| RDS PostgreSQL instance | 12.41 | 25.55 |
| RDS storage | 2.54 | 5.08 |
| ElastiCache Redis | 12.41 | 24.82 |
| Load balancer (hours and capacity) | 18.98 | 21.32 |
| Public IPv4 addresses | 18.25 | 10.95 |
| NAT gateway | 0 | 35.23 |
| CloudWatch logs, alarms and metrics | 1.60 | 2.50 |
| Secrets Manager, ECR, S3, Route 53 | 1.40 | 1.40 |
| CloudFront, SES, access logs | 0.31 | 0.53 |
| **Total** | **112.96** | **172.43** |

Largest items in production-like: Fargate (26%), NAT gateway (20%), RDS Multi-AZ (18%), Redis (14%), load balancer (12%).

## Findings

1. **Public IPv4 addresses cost 0.005 a hour each (3.65 a month).** The demo has no NAT, so each of 3 tasks holds an address, and the ALB holds 2. That is 18.25 a month, 16% of the demo bill. The first estimate in ADR 0003 left this out.
2. **A NAT gateway is cheaper than VPC endpoints at this size.** NAT with its address costs 38.69 a month. The four endpoints needed (ECR API, ECR Docker, Secrets Manager, CloudWatch Logs) in two zones cost 64.24. Endpoints win only above about 670 GB a month through NAT.
3. **Traffic is cheap until it is large.** CloudFront gives 1 TB and 10 million requests every month at no cost. At 2 million requests a month, traffic changes the bill by less than 5. At 40 million it adds about 65: CloudFront requests (about 36), then logs and load balancer capacity.
4. **Multi-AZ doubles the database and cache.** That is 15.68 more a month for RDS (instance and storage) and 12.41 for the second Redis node. It buys failover. It is the right trade for production and the wrong one for a demo.
5. **ARM saves about 20% on compute.** Fargate ARM costs 0.03238 per vCPU-hour against 0.04048. This saves 9 a month in production-like. It needs an `arm64` image, which fits the CI image build in [#44](https://github.com/massimoselvi/seatlock/issues/44).

## Cheapest safe demo

**Demo lean: about 86 to 89 a month, or 0.12 an hour.**
- 1 web task and 1 worker, on ARM, one AZ, no NAT.
- It keeps the same security rules as production: private database, encryption, secrets in Secrets Manager.
- Do not put real user data in it. One AZ and one web task give no failover.

A validation deploy for [#43](https://github.com/massimoselvi/seatlock/issues/43) costs about **3 for one day** and about **9 for three days**. Destroy the stacks afterwards. A destroyed demo costs nothing.

## Idle cost

| Action | Saves | Remaining |
|--------|-------|-----------|
| Scale tasks to zero | about 56 a month | about 57 a month (database, Redis, ALB, addresses) |
| Stop the RDS instance (up to 7 days) | about 12 a month | storage still billed |
| **Destroy the demo** | everything | 0, and the data is gone |

For a demo, destroy it between sessions. Keep production running.

## Recommendation

1. **Demo and validation:** use the demo lean setup, run it for a day, then destroy it. Budget about 3.
2. **Production:** start with the production-like setup, on ARM once [#44](https://github.com/massimoselvi/seatlock/issues/44) builds `arm64` images. Budget **160 to 175 a month**. Add WAF (about 10) when the app takes real traffic.
3. **Set a budget alarm at 200 a month** in AWS Budgets before the first deploy. The model puts production-like at 160 to 175 for a long time. A bill above 200 means more traffic than assumed, or something is wrong.
4. **Re-run the model with real traffic** after the first month and update this file.

## Not modelled

- **Savings Plans and Reserved Instances.** Commitments for Fargate and RDS can cut the fixed costs a lot. They need a stable load first. Price them with the AWS Pricing Calculator.
- **Fargate Spot** for the worker. It has no fixed list price. The worker is safe to interrupt because promotions are idempotent ([ADR 0002](adr/0002-enqueue-celery-tasks-on-commit.md)). Test it in the demo.
- **Data transfer between zones**, charged per GB in each direction. Small here.
- **Domain registration, taxes, support plans** and any free credits on the account.
- **Growth in the database** beyond 20 GB, and backups above the free allowance (equal to the database size).

## Sources

AWS Price List Bulk API, `eu-west-1`, versions: ECS 2026-10-19, RDS 2026-10-20, ElastiCache 2026-10-14, ELB 2026-09-11, VPC 2026-10-16, EC2 (NAT) 2026-10-15, CloudWatch 2026-10-07, S3 2026-10-15, WAF 2026-09-14, CloudFront 2026-10-19, SES, Secrets Manager, ECR and Route 53.
CloudFront, WAF and Route 53 are global services. Their prices are the same for this use.
The AWS pricing tools in this session did not connect, so the numbers come from the public price files, not from the AWS Pricing Calculator. Check the totals in the calculator before you commit a budget.
