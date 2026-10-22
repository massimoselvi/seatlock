# Runbook: queue backlog

**Trigger:** the Celery queue holds more than 100 tasks for 10 minutes.
Impact: waitlisted users are not promoted after a cancel. Seat counts stay correct.

## 1. Check the worker

- Is the worker service running? In ECS, check the task count and recent stops.
- Read the worker log for `ready` and for repeating errors.

## 2. Check Redis

- Is Redis reachable? Check memory use and evictions. An evicted queue key loses tasks.

## 3. Act

| Finding | Action |
|---------|--------|
| Worker down | Restart the service. Tasks wait in Redis. |
| Worker slow | Scale workers up. Check for slow email sending. |
| Poison task | Find the task in the log, fix the cause, then purge only that task type. |

## 4. Recover missed promotions

The `promote_waitlist` task is idempotent. After the queue is healthy, run it for each workshop that has free seats and a waitlist:

```python
from infrastructure.db.models import Workshop
from infrastructure.messaging.tasks import promote_waitlist
for w in Workshop.objects.all():
    promote_waitlist.delay(w.pk)
```

## 5. Follow up

See [ADR 0002](../adr/0002-enqueue-celery-tasks-on-commit.md). A task can be lost if the process dies between commit and send. A periodic sweep that runs the loop above removes that gap.
