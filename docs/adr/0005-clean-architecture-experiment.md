# 0005. Clean Architecture for the backend (experiment)

Status: **Experiment. Not accepted.** Lives on the `exp/clean-arch-*` branches only.

## Context

The backend is one Django app, `workshops`. Models, seat rules, views and tasks sit side by side.
That works at this size. The question is whether the layering in
["Clean Architecture in Django" (Shiladitya Majumder, 2025)](https://shiladityamajumder.medium.com/clean-architecture-in-django-a-practical-real-world-project-structure-1f4c89e402f0)
earns its cost here, in the part of the system that matters most: seat allocation ([ADR 0001](0001-row-locks-for-seat-allocation.md)).

The article's rule: dependencies point inward only. Domain has no Django. Use cases depend on interfaces. Infrastructure implements them. Views wire it together.

## What was built

Four stacked branches. Each one runs, passes every test and leaves the API unchanged.

| Branch | Adds |
|--------|------|
| `exp/clean-arch-1-domain` | `domain/`: `Workshop` and `Registration` entities with the seat rules. Plain Python. |
| `exp/clean-arch-2-application` | `application/`: ports (`interfaces.py`), DTOs and three use cases: `RegisterForWorkshop`, `CancelRegistration`, `PromoteWaitlist`. |
| `exp/clean-arch-3-infrastructure` | `infrastructure/`: ORM models and migrations, repositories, unit of work, cache, mailer, Celery adapters, composition root. |
| `exp/clean-arch-4-interface` | `interface/api/`: views and serializers split by context. A test that enforces the import rules. Tests grouped by layer. |

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
|---------|------|-----|
| ORM model in `interface/api/orders/models.py`, imported by infrastructure | Models in `infrastructure/db` | The article's version makes infrastructure depend on the interface layer, which breaks its own rule. |
| Repositories only | Repositories **and a `UnitOfWork` port** | The seat rule needs a transaction, a row lock (`select_for_update`) and "run after commit". Those are the point of ADR 0001 and ADR 0002. A repository alone cannot express them. |
| View builds the use case | `infrastructure/container.py` builds it | One place picks concrete classes. Views and Celery tasks share it. |
| Everything behind a use case | Reads and accounts call Django directly | List and dashboard queries hold no rules. Sign-up and login are Django's own auth. A use case there adds files and no protection. |
| Django app label from the package | `infrastructure.db` has label `workshops` | Tables (`workshops_workshop`) and migration history stay the same. `makemigrations --check` is clean. |

The Celery task keeps its old name (`workshops.tasks.promote_waitlist`), so messages already queued stay valid.

## Results

| | `main` | Experiment |
|---|-------:|-----------:|
| App code (excluding migrations and tests) | 14 files, 631 lines | 29 files, 1,029 lines |
| Tests | 41 tests, 9 files, 513 lines | 73 tests, 13 files, 951 lines |
| Tests that run with no database | 0 | 26, in 0.07 s |
| Full suite | about 17 s | about 17 s |
| Files to read to follow "register" | 3 (view, service, model) | 6 (view, container, use case, ports, repository, model) |

Checked on the running stack too: register, waitlist, cancel and the Celery promotion return the same JSON as before.

## What got better

- **The seat rules are testable without a database.** 13 pure tests on the entities and 13 use-case tests on in-memory fakes run in 0.07 s. On `main`, every seat test needs Postgres.
- **The lock rule became a test.** The fake repository fails any use case that reads seat counts without locking the workshop first (`test_seat_counts_are_only_read_under_the_workshop_lock`). On `main` only the slow concurrency test guards this.
- **Side effects are explicit and ordered.** Cache invalidation and promotion run only after commit. Email runs after the transaction closes. A test proves a failure triggers none of them.
- **The layers are enforced.** `tests/test_architecture.py` fails the build if domain or application import Django, DRF or Celery, or if infrastructure imports the interface layer.
- **The concurrency test still passes** against the real unit of work, so the locking was not lost in the move.

## What got worse

- **63% more code and 15 more files** for the same behavior. Part of it is mapping: the ORM `Workshop` and the domain `Workshop` hold the same fields, and repositories convert both ways.
- **More indirection.** A change to "what happens on cancel" touches the use case, a port and often a repository.
- **Two models per concept.** Add a field and you edit the ORM model, the entity, the repository mapping and the serializer.
- **Little gain on reads and accounts**, which is why they stay outside the use-case layer. That makes the architecture partial on purpose.
- **The rules are small.** `domain/` is 89 lines. The risk the layering reduces is real, but the surface it protects is small today.

## Verdict (opinion, for you to overrule)

Do not adopt it wholesale. The cost is high for a codebase this size, and most of the new files only move data between layers.

Two pieces are worth keeping even if the rest is dropped:

1. **The `UnitOfWork` port with the in-memory fake.** It encodes the lock and after-commit rules and makes them cheap to test.
2. **The architecture test.** It costs one file and prevents drift.

A middle path: keep the current `workshops` app, move only the seat rules into plain entities and use cases, and keep Django models and views where they are. That would keep most of the testing benefit with much less new code. It would be worth trying as `exp/clean-arch-lite`.

If the project grows a second delivery channel (a CLI, an admin import, a websocket) or the rules grow a lot, the full layering pays off. Revisit then.

## The lite variant (`exp/clean-arch-lite`)

Cut from `main`, not stacked on the others. It keeps the `workshops` app, the Django models, the views and the ORM calls in `services.py`. The only change: the seat **decisions** move into `workshops/rules.py`, plain functions with standard-library imports only. `services.py` loads rows, calls the rules, saves, and keeps all locking and transactions.

| | `main` | Lite | Full (branch 4) |
|---|-------:|-----:|----------------:|
| App code | 14 files, 631 lines | 15 files, 694 lines (+10%) | 29 files, 1,029 lines (+63%) |
| Tests | 41 | 57 | 73 |
| Tests with no database | 0 | 16, in 0.08 s | 26, in 0.07 s |
| `services.py` | 77 lines | 78 lines | replaced by 3 use cases |
| Lock rule guarded by a fast test | no | **no** | yes |
| After-commit and rollback behavior tested without a database | no | **no** | yes |
| Layer rule enforced by a test | no | yes (`rules.py` is pure) | yes (4 layers) |

**What lite keeps:** the decision rules are unit-tested without a database, a test guards the one duplicated enum, and a test keeps `rules.py` free of Django. It costs one new module and about 63 lines.

**What lite gives up:** the three guarantees that matter most for seat integrity live in `services.py`, next to the ORM. They are the row lock, the "side effects only after commit" order, and "a failure triggers no side effect". Lite cannot test those without Postgres. The full version tests them in 0.07 s with the in-memory fake.

**Honest reading:** the rules lite extracts are small (about 60 lines). It proves the idea but protects little. The part of the full version that protects the most is the unit-of-work port with its fake, and lite does not have it.

### Updated verdict

1. **Lite is the cheapest step and is safe to merge.** It changes no behavior, passes every test, and adds 16 fast tests. Take it if you want a foothold without a refactor.
2. **Full is not worth it today**, for the cost reasons above.
3. **The best next experiment is lite plus a unit-of-work port**: keep Django models and views, add only the `UnitOfWork` interface, one in-memory fake, and the three use cases. That recovers the lock and after-commit tests for a fraction of the full version's files. Try it as `exp/clean-arch-6-lite-uow`.

## How to review

```bash
git diff --stat main...exp/clean-arch-4-interface
git log --oneline main..exp/clean-arch-4-interface
docker compose run --rm web pytest tests/unit      # the 26 database-free tests
docker compose run --rm web pytest tests/test_architecture.py
```
