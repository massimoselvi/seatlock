# 2. Enqueue Celery tasks on commit

Date: 2026-10-20

## Status

Accepted

## Context

A cancel frees a seat and must promote the first waiting user. If the task is sent before the transaction commits, the worker can run against data that is not visible yet. If the transaction rolls back, the task still runs.

## Decision

Enqueue every task with `transaction.on_commit`. Tasks are idempotent: running one twice gives the same result.

## Alternatives

- **Send the task inside the transaction.** Simple, but it races with the commit.
- **Transactional outbox table.** It gives stronger delivery guarantees but adds a table and a relay process. It is too heavy for this scope.

## Consequences

- A task is sent only for committed changes.
- If the process crashes between the commit and the send, the promotion is lost. The `sweep_waitlists` task repairs it: it runs every 5 minutes and queues a promotion for each workshop with a free seat and a waitlist (added 2026-10-23). A lost promotion therefore delays a waiting user by at most one interval.
