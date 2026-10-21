# Runbook: high error rate or slow registration

**Trigger:** 5xx above 2% for 5 minutes, or registration p95 above 800 ms for 10 minutes.

## 1. Scope

- Is it all endpoints or only register and cancel?
- Did it start at a deploy? If yes, roll back first, investigate after.

## 2. Check dependencies

| Check | Symptom | Action |
|-------|---------|--------|
| Database CPU and connections | Timeouts, `too many connections` | Scale the instance, lower the per-worker pool |
| Lock waits on one workshop | Slow register for a popular workshop | Expected under a burst. The row lock serializes that workshop only. Check the rate limit. |
| Redis down | Errors on throttling or cache | Cache and throttle failures must not break reads. Restore Redis. |
| Container restarts | Out-of-memory kills | Raise memory, check for leaks |

## 3. Roll back

Redeploy the previous task definition. Migrations are backwards compatible, so the old code runs on the new schema.

## 4. Follow up

Record the cause, the time to detect and the time to recover. Update the thresholds in [slo.md](../slo.md) if the alarm was late or noisy.
