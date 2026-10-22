# 5. Clean Architecture for the backend

Date: 2026-10-22

## Status

Accepted (2026-10-22). It began as an experiment on the `exp/clean-arch-*` branches. The structure of `exp/clean-arch-4-interface` is now the backend structure.

This ADR keeps its original file name so that existing links stay valid.
It moves the code that [ADR 0001](0001-row-locks-for-seat-allocation.md) and [ADR 0002](0002-enqueue-celery-tasks-on-commit.md) describe. Both decisions still stand.
How the code works is in [docs/architecture.md](../../architecture.md).

## Context

The backend was one Django app, `workshops`. Models, seat rules, views and tasks sat side by side.
That works at this size. The question was whether the layering in
["Clean Architecture in Django" (Shiladitya Majumder, 2025)](https://shiladityamajumder.medium.com/clean-architecture-in-django-a-practical-real-world-project-structure-1f4c89e402f0)
earns its cost here, in the part of the system that matters most: seat allocation ([ADR 0001](0001-row-locks-for-seat-allocation.md)).

The article's rule: dependencies point inward only. Domain has no Django. Use cases depend on interfaces. Infrastructure implements them. Views wire it together.

## Decision

Adopt the four-layer structure built in `exp/clean-arch-4-interface`.

1. **Dependencies point inward.** `domain` imports only the standard library. `application` imports `domain`. `infrastructure` imports both. `interface` may import all of them.
2. **Seat rules live in `domain/`.** Workflows live in `application/` as three use cases: `RegisterForWorkshop`, `CancelRegistration`, `PromoteWaitlist`. Views and Celery tasks never hold a business rule.
3. **A `UnitOfWork` port carries the transaction.** It expresses the row lock, the commit and "run after commit". The Django adapter uses `transaction.atomic`, `select_for_update()` and `transaction.on_commit`. A fake implements the same port for fast tests.
4. **One composition root.** `infrastructure/container.py` is the only place that picks concrete classes.
5. **Reads and accounts stay outside the use cases.** List and dashboard queries hold no rules. Sign-up and login are Django's own auth.
6. **A test enforces the layers.** `tests/test_architecture.py` fails the build on a forbidden import.
7. **Storage does not change.** The ORM app keeps the label `workshops`, so table names and the migration history are the same. The Celery task keeps its old name, `workshops.tasks.promote_waitlist`, so queued messages stay valid.

The lite variant (`exp/clean-arch-lite`) is **not** adopted. Its comparison is kept below for the record. Its code is kept at the tag `archive/clean-arch-lite`.

## What was built

Four stacked branches. Each one runs, passes every test and leaves the API unchanged.

| Branch | Adds |
| --- | --- |
| `exp/clean-arch-1-domain` | `domain/`: `Workshop` and `Registration` entities with the seat rules. Plain Python. |
| `exp/clean-arch-2-application` | `application/`: ports (`interfaces.py`), DTOs and three use cases: `RegisterForWorkshop`, `CancelRegistration`, `PromoteWaitlist`. |
| `exp/clean-arch-3-infrastructure` | `infrastructure/`: ORM models and migrations, repositories, unit of work, cache, mailer, Celery adapters, composition root. |
| `exp/clean-arch-4-interface` | `interface/api/`: views and serializers split by context. A test that enforces the import rules. Tests grouped by layer. |

The four branches were merged to `main` in PR #75 and then deleted. Their commits are in the history of `main`: `git log --oneline f681d12^..8f31c89`.

```
backend/
  config/            settings, urls, celery
  domain/workshops/  entities.py, exceptions.py
  application/workshops/  interfaces.py, services.py, dto.py
  infrastructure/    db/ (models, migrations, repositories, unit_of_work, queries)
                     cache/  messaging/  notifications/  container.py
  interface/api/     workshops/  organizer/  accounts/  urls.py
  tests/             unit/ (domain, application)  integration/  api/  config/
```

## Where this differs from the article

| Article | Here | Why |
| --- | --- | --- |
| ORM model in `interface/api/orders/models.py`, imported by infrastructure | Models in `infrastructure/db` | The article's version makes infrastructure depend on the interface layer, which breaks its own rule. |
| Repositories only | Repositories **and a `UnitOfWork` port** | The seat rule needs a transaction, a row lock (`select_for_update`) and "run after commit". Those are the point of ADR 0001 and ADR 0002. A repository alone cannot express them. |
| View builds the use case | `infrastructure/container.py` builds it | One place picks concrete classes. Views and Celery tasks share it. |
| Everything behind a use case | Reads and accounts call Django directly | List and dashboard queries hold no rules. Sign-up and login are Django's own auth. A use case there adds files and no protection. |
| Django app label from the package | `infrastructure.db` has label `workshops` | Tables (`workshops_workshop`) and migration history stay the same. `makemigrations --check` is clean. |

## Results

Measured on 2026-10-22 on clean checkouts, against PostgreSQL 17 in Docker. Code size excludes `__init__.py`, migrations and tests.

| | `main` | Lite | Full (accepted) |
| --- | ---: | ---: | ---: |
| App code | 14 files, 631 lines | 15 files, 694 lines (+10%) | 29 files, 1,029 lines (+63%) |
| Tests | 41 tests, 9 files, 513 lines | 57 tests, 11 files, 606 lines | 73 tests, 13 files, 951 lines |
| Tests that run with no database | 0 | 16, in 0.06 s | 32, in 0.08 s |
| Full suite | about 17 s | about 17 s | about 17 s |
| Files to read to follow "register" | 3 | 3 | 6 |

The database-free count includes the architecture tests: 14 rule tests and 2 architecture tests for lite, and 26 unit tests and 6 architecture tests for full. An earlier version of this table compared lite with the architecture tests (16) against full without them (26). That was not like for like.

Checked on the running stack too: register, waitlist, cancel and the Celery promotion return the same JSON as before.

Tests by directory in the accepted structure: `unit/domain` 13, `unit/application` 13, `integration` 4, `api` 29, `config` 8, `test_architecture.py` 6. Total 73.

## Evidence: why full and not lite

The two variants were compared by breaking the seat logic on a scratch copy of each and running the tests.

| Bug introduced | Lite | Full |
| --- | --- | --- |
| Remove `select_for_update()` from the real lock | Only the Postgres concurrency test fails. | Only the Postgres concurrency test fails. |
| Read the confirmed seat count before taking the lock (promote path) | **All 57 tests pass.** | **4 tests fail in 0.11 s**, including `test_seat_counts_are_only_read_under_the_workshop_lock`. |

- Neither variant proves the real database lock with a fast test. Only `test_concurrent_registrations_never_oversell` does, and it needs PostgreSQL.
- Only the full variant guards the **order** of calls inside a use case. The fake repository fails any read of seat counts that happens before the lock.
- Lite adds tests, but the guarantees that matter most for seat integrity stay in `services.py`, next to the ORM.

## What got better

- **The seat rules are testable without a database.** 13 pure tests on the entities and 13 use-case tests on in-memory fakes run in milliseconds. Before, every seat test needed Postgres.
- **The lock rule became a test.** The fake repository fails any use case that reads seat counts without locking the workshop first (`test_seat_counts_are_only_read_under_the_workshop_lock`).
- **Side effects are explicit and ordered.** Cache invalidation and promotion run only after commit. Email runs after the transaction closes. A test proves a failure triggers none of them.
- **The layers are enforced.** `tests/test_architecture.py` fails the build if domain or application import Django, DRF or Celery, or if infrastructure imports the interface layer.
- **The concurrency test still passes** against the real unit of work, so the locking was not lost in the move.

## What got worse

- **63% more code and 15 more files** for the same behavior. Part of it is mapping: the ORM `Workshop` and the domain `Workshop` hold the same fields, and repositories convert both ways.
- **More indirection.** A change to "what happens on cancel" touches the use case, a port and often a repository.
- **Two models per concept.** Add a field and you edit the ORM model, the entity, the repository mapping and the serializer.
- **Little gain on reads and accounts**, which is why they stay outside the use-case layer. That makes the architecture partial on purpose.
- **The rules are small.** `domain/` is 89 lines. The risk the layering reduces is real, but the surface it protects is small today.

The experiment's first verdict advised against adopting the full layering on cost grounds. The cost above is accepted knowingly. Revisit if the cost grows faster than the value, for example when a second delivery channel (a CLI, an import job, a websocket) does not appear and the layering stays a mapping exercise.

## Consequences

- New code goes where [docs/architecture.md](../../architecture.md) says. The PR template and `CODEOWNERS` point at the new paths.
- ADR 0001 and ADR 0002 stay valid. Their file references now point at `domain/`, `application/` and `infrastructure/db/repositories.py`.
- The concurrency test is the only proof of the real lock. Keep it, and do not delete it for speed.
- `exp/clean-arch-lite` is closed as an alternative. The tag `archive/clean-arch-lite` keeps its code. The follow-up experiment `exp/clean-arch-6-lite-uow` is dropped, because the full variant already has the unit-of-work port.

## Known gaps and follow-ups

These are real and not yet fixed.

1. **Fixed (2026-10-22): no drift test for the status enum.** The domain `RegistrationStatus` and the ORM `Registration.Status` are still two lists, because the domain cannot import Django. `tests/test_status_mapping.py` now fails the build if they differ. It needs no database. With a status added only to the model, two of its three tests fail.
2. **Fixed (2026-10-22): `seats_left` was computed twice.** `WorkshopSerializer.get_seats_left` now calls `Workshop.free_seats` in the domain.
3. **A promotion email can be lost.** Email is sent after commit, outside the transaction. A worker crash between the commit and the send loses the email. The seat is still confirmed.
4. **A queued promotion can be lost.** Unchanged from ADR 0002: a crash between commit and enqueue loses the task. A periodic sweep would close the gap.
5. **The architecture test covers imports only.** It cannot see a business rule that sits in a view. Review and `CODEOWNERS` cover that.

## Alternatives considered

- **Keep `main` as it was.** The cheapest option. Seat tests all need Postgres and the lock order is guarded only by the slow concurrency test.
- **Lite (`exp/clean-arch-lite`, tag `archive/clean-arch-lite`).** One new module, `workshops/rules.py`, with plain decision functions. It costs +10% code. It tests the decisions without a database but leaves the lock, the after-commit order and rollback behavior untestable without Postgres. Rejected.
- **Lite plus a unit-of-work port.** Proposed as a next experiment, never built. The accepted structure already contains the port, so this option is dropped.

### The lite variant in detail

Cut from `main`, not stacked on the others. It keeps the `workshops` app, the Django models, the views and the ORM calls in `services.py`. The only change: the seat **decisions** move into `workshops/rules.py`, plain functions with standard-library imports only. `services.py` loads rows, calls the rules, saves, and keeps all locking and transactions.

| | `main` | Lite | Full |
| --- | ---: | ---: | ---: |
| `services.py` | 77 lines | 78 lines | replaced by 3 use cases |
| Lock rule guarded by a fast test | no | no | yes |
| After-commit and rollback behavior tested without a database | no | no | yes |
| Layer rule enforced by a test | no | yes (`rules.py` is pure) | yes (4 layers) |
| Enum drift guarded by a test | n/a | yes | no at first, **yes** since gap 1 was fixed |

## How to review

```bash
git log --oneline f681d12^..8f31c89                       # the experiment, step by step
git diff --stat f31411b archive/clean-arch-lite -- backend  # the lite variant against the old main
docker compose run --rm web pytest tests/unit      # the 26 database-free unit tests
docker compose run --rm web pytest tests/test_architecture.py
```
