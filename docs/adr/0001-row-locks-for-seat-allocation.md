# 0001. Use row locks for seat allocation

Status: Accepted

## Context

Two users can ask for the last seat at the same time. A read-then-write check lets both succeed and oversells the workshop.

## Decision

Every change to seat counts runs in `transaction.atomic` and locks the Workshop row with `select_for_update()`. The rules live in `workshops/services.py`. Database constraints back up the code: capacity is greater than 0, and a user has one active registration per workshop.

## Alternatives

- **Optimistic locking with a version column.** It needs retries under load and more code in each caller.
- **Serializable isolation.** It gives the same safety but aborts transactions at random and hides the rule in a database setting.
- **A counter in Redis.** It adds a second source of truth that can drift from Postgres.

## Consequences

- Requests for the same workshop queue on one row. Requests for different workshops do not block each other.
- Tests need real Postgres. A threaded concurrency test checks that seats are never oversold.
