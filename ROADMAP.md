# Roadmap

Seatlock sells seats for workshops. A seat must never be oversold.

## v0.1 Foundation (done)

- Models and database constraints
- Seat allocation and waitlist promotion
- Read-only workshops API, Vue list page
- Docker Compose stack and CI

## v0.2 Registration

- Authentication
- Register and cancel API
- Registration UI

Exit criteria: a user can register, join the waitlist and cancel. Concurrency tests pass.

## v0.3 Operations

- Organizer dashboard
- Rate limiting and caching
- Service level objectives, alarms and a runbook

Exit criteria: documented SLOs. Alarms exist for queue backlog and error rate.

## v0.4 Deploy

- AWS target architecture and cost estimate
- Infrastructure as code with AWS CDK
- Deploy and rollback plan

Exit criteria: `cdk synth` passes in CI. The architecture is documented in ADRs.

## Out of scope

- Payments
- Multi-tenant organizations
- Native mobile apps

## Key risks

| Risk | Mitigation |
|------|------------|
| Overselling under concurrent requests | Row lock with `select_for_update()`, database constraints, concurrency test |
| Lost waitlist promotion | Task enqueued with `transaction.on_commit`, idempotent task |
| Cost of idle cloud resources | Cost estimate in ADR, small instance sizes |
