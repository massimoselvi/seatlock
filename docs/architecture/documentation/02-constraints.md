## Constraints

| Constraint | Source |
|------------|--------|
| Seat counts change only inside a transaction that holds a row lock on the workshop. | ADR 0001 |
| A task is sent to the queue only after the transaction commits. | ADR 0002 |
| PostgreSQL must be a real PostgreSQL, reached by direct connections or a pooler in session mode. Row locks break in statement mode. | ADR 0003 |
| Domain and application code never import Django, Django REST Framework or Celery. | ADR 0005, `tests/test_architecture.py` |
| The ORM app label is `workshops` and the Celery task name is `workshops.tasks.promote_waitlist`. Table names, migrations and queued messages depend on them. | ADR 0005 |
| Infrastructure is code (AWS CDK in Python). Demo and production differ by values, not by code. | ADR 0004 |
| Frontend colors come from tokens, and class names are complete static strings. | ADR 0006 |

## Known gaps

- CloudFront reaches the load balancer over HTTP.
- A promotion email or a queued promotion can be lost if a process dies after the commit.
- Staff edits in the Django admin bypass the use cases and the lock. The admin is off in AWS.
- Two alarms from the SLO document have no metric source yet.
