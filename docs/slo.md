# Service level objectives

Scope: the public API (`/api/`). Window: rolling 30 days.

| SLI | How we measure it | SLO |
|-----|-------------------|-----|
| Availability | Share of requests that do not return 5xx | 99.5% |
| Read latency | p95 of `GET /api/workshops/` | under 300 ms |
| Registration latency | p95 of `POST .../register/` and `.../cancel/` | under 800 ms |
| Seat integrity | Workshops with more confirmed registrations than capacity | **0, always** |
| Waitlist promotion | Time from a cancel to the promoted user's confirmation | p95 under 60 s |

Seat integrity is not a budget. One oversold workshop is an incident.

## Error budget

99.5% availability over 30 days allows about 3 h 36 min of failed requests.
When more than half of the budget is gone, stop feature work and fix reliability first.

## Alarms

Each alarm links to a runbook. Thresholds are the starting point and need tuning with real traffic.

| Alarm | Condition | Severity | Runbook |
|-------|-----------|----------|---------|
| Oversold workshop | Check query returns any row (every 5 min) | Page | [seats-oversold](runbooks/seats-oversold.md) |
| Queue backlog | Celery queue length above 100 for 10 min | Page | [queue-backlog](runbooks/queue-backlog.md) |
| High error rate | 5xx above 2% of requests for 5 min | Page | [high-error-rate](runbooks/high-error-rate.md) |
| Slow registration | p95 above 800 ms for 10 min | Ticket | [high-error-rate](runbooks/high-error-rate.md) |
| Database connections | Above 80% of the limit for 10 min | Ticket | [high-error-rate](runbooks/high-error-rate.md) |
| Throttling spike | 429 above 20% of requests for 10 min | Ticket | Check for abuse or a client retry loop |

The AWS metrics and alarms are defined as code in the CDK stack (milestone v0.4).
