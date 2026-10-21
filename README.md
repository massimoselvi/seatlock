# Seatlock

Workshops and classes with limited seats - built so a seat can never be sold twice.

**Stack:** Django 6 · Django REST Framework · PostgreSQL · Celery + Redis · Vue 3 (Vite, TypeScript) · Docker Compose · GitHub Actions

## Why it's interesting

- **No overselling under concurrency.** Registration locks the workshop row (`SELECT ... FOR UPDATE`) inside a transaction, so simultaneous requests are serialized. A test fires 20 threads at a 5-seat workshop and asserts exactly 5 confirmed and 15 waitlisted.
- **Database-level guarantees.** Check and partial unique constraints enforce positive capacity and one active registration per user per workshop, even if application code is bypassed.
- **Waitlist with async promotion.** Cancelling a confirmed seat schedules a Celery task via `transaction.on_commit`, which promotes the oldest waitlisted person and emails them.
- **Idempotent registration.** Retrying the same request returns the existing registration.

## Run it

```bash
docker compose up --build
```

| Service  | URL                                |
|----------|------------------------------------|
| Frontend | http://localhost:5173              |
| API      | http://localhost:8000/api/workshops/ |
| Admin    | http://localhost:8000/admin/       |

```bash
docker compose exec web python manage.py createsuperuser
docker compose run --rm web pytest      # tests run against real Postgres
docker compose run --rm web ruff check .
```

## Layout

```
backend/    Django project (config/) and the workshops app: models, services, tasks, API
frontend/   Vue 3 + Vite + TypeScript
compose.yaml  db, redis, web, worker, frontend
```

Business rules live in `backend/workshops/services.py`, not in views, so they are easy to test and reuse.

## Alternative version to check

The branch [`xp/clean-arch-lite`](https://github.com/massimoselvi/seatlock/tree/xp/clean-arch-lite) is an experiment. It is not part of `main`.

It moves the seat decisions into plain functions in `backend/workshops/rules.py`, which imports only the standard library. Django models, views and the row locking stay where they are. The change is small: one new module, about 60 lines. It adds 16 tests that run without a database.

```bash
git diff --stat main...xp/clean-arch-lite
```

The comparison with a full Clean Architecture refactor is in [ADR 0005](https://github.com/massimoselvi/seatlock/blob/exp/clean-arch-4-interface/docs/adr/0005-clean-architecture-experiment.md).

## Roadmap

- [x] Models, constraints, seat allocation service, waitlist promotion task
- [x] Read-only workshops API, Vue list page, CI
- [ ] Auth, register/cancel API endpoints and UI
- [ ] Organizer dashboard
- [ ] Rate limiting and caching on the public list
- [ ] Deployment (AWS)
