# Seatlock backend

Django 6 and Django REST Framework API for workshops with limited seats. A seat can never be sold twice.

**Stack:** Django · DRF · PostgreSQL · Celery · Redis · uv · pytest · ruff

## Layout

```
backend/
  config/        settings, root urls, Celery app, wsgi and asgi
  workshops/     the only Django app
    models.py        Workshop, Registration and their database constraints
    services.py      seat rules: register, cancel, promote the waitlist
    tasks.py         Celery task that promotes the waitlist and sends email
    cache.py         versioned cache of the public workshops list
    serializers.py   JSON shapes
    views.py         DRF views and viewsets (no business rules)
    urls.py          all API routes
  tests/         pytest suite (needs PostgreSQL)
  Dockerfile     image used by the web and worker services
  pyproject.toml dependencies and tool settings
  uv.lock        locked dependency versions
```

## Design rules

- **Business rules live in `workshops/services.py`**, never in views.
- **Seat changes lock the workshop row.** Every function that changes seat counts calls `select_for_update()` inside `transaction.atomic`. Concurrent requests for one workshop queue up, so capacity cannot be oversold.
- **Database constraints back up the code.** Capacity must be above zero. A user can hold only one active (confirmed or waitlisted) registration per workshop.
- **Celery tasks are enqueued with `transaction.on_commit`.** A task never runs for a change that rolled back.
- **Registration is idempotent.** Repeating a request returns the existing registration.

See [ADR 0001](../docs/adr/0001-row-locks-for-seat-allocation.md) and [ADR 0002](../docs/adr/0002-enqueue-celery-tasks-on-commit.md).

## Run it

Use Docker. It starts PostgreSQL, Redis, the API, the worker and the frontend:

```bash
docker compose up --build      # from the repository root; API on http://localhost:8000
```

Without Docker you need PostgreSQL and Redis running, and a `.env` file (see `../.env.example`):

```bash
cd backend
uv sync
uv run python manage.py migrate
uv run python manage.py runserver
uv run celery -A config worker --loglevel=info    # in a second terminal
```

Create a staff user for the organizer dashboard:

```bash
docker compose exec web python manage.py createsuperuser
```

## Configuration

Read from the environment, or from `../.env` for local runs.

| Variable | Default | Meaning |
|----------|---------|---------|
| `DEBUG` | `false` | Debug mode. With it off, the app refuses to start without `SECRET_KEY`. |
| `SECRET_KEY` | none | Django secret. **Required when `DEBUG` is off.** |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1,web` | Accepted host names, comma separated. |
| `DATABASE_URL` | `postgres://seatlock:seatlock@localhost:5432/seatlock` | PostgreSQL connection. |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Celery broker and result backend. |
| `CACHE_URL` | `redis://localhost:6379/1` | Redis cache, also used for throttle counters. |
| `WORKSHOP_LIST_CACHE_SECONDS` | `30` | How long the public list stays cached. |
| `NUM_PROXIES` | `0` | Proxies in front of the app. DRF reads the client IP from the right end of `X-Forwarded-For`. Use `2` behind CloudFront and an ALB. |
| `FORCE_HTTPS` | `false` | Turns on the HTTPS redirect, secure proxy header and HSTS. |
| `ADMIN_ENABLED` | `true` | Mounts `/admin/`. Production turns it off. |
| `EMAIL_BACKEND` | console backend | Where waitlist emails go. |
| `CELERY_TASK_ALWAYS_EAGER` | `false` | Run tasks inline. The tests set it. |

## API

All routes are under `/api/`. Reads are public. Writes need a token: `Authorization: Token <key>`.

| Method and path | Who | Purpose |
|-----------------|-----|---------|
| `GET /health/` | anyone | Liveness check. |
| `POST /auth/signup/` | anyone | Create an account. Returns a token. |
| `POST /auth/login/` | anyone | Exchange a username and password for a token. |
| `POST /auth/logout/` | user | Delete the token. |
| `GET /auth/me/` | user | The current user, with `is_staff`. |
| `GET /workshops/` | anyone | Paginated list with `seats_taken` and `seats_left`. Cached. |
| `POST /workshops/{id}/register/` | user | Confirm a seat or join the waitlist. |
| `GET /registrations/` | user | The user's own registrations. |
| `POST /registrations/{id}/cancel/` | user | Cancel. A freed seat promotes the oldest waitlisted user. |
| `GET /organizer/workshops/` | staff | Seats taken, seats left and waitlist size. |
| `GET /organizer/workshops/{id}/registrations/` | staff | Who registered, with status. |

### Rate limits

| Scope | Limit | Applies to |
|-------|-------|-----------|
| `registration` | 10 per minute | register and cancel |
| `login` | 10 per minute | login |
| `auth` | 10 per minute | signup |
| `anon` / `user` | 60 / 120 per minute | everything else |

### Cache

`GET /workshops/` is cached in Redis. The key holds only the page number. Register, cancel and waitlist promotion invalidate the cache after commit, through a version number.

## Tests

The suite needs real PostgreSQL. The concurrency test fires 20 threads at a 5-seat workshop and expects exactly 5 confirmed and 15 waitlisted. Run it in Docker:

```bash
docker compose run --rm web pytest
docker compose run --rm web ruff check .
docker compose run --rm web ruff format --check .
docker compose run --rm web python manage.py makemigrations --check --dry-run
```

| File | Covers |
|------|--------|
| `test_services.py` | seat rules, waitlist, idempotency, concurrency |
| `test_registration_api.py` | register and cancel over HTTP |
| `test_organizer_api.py` | staff-only dashboard endpoints |
| `test_auth.py` | signup, login, logout, `me` |
| `test_throttling_and_cache.py` | rate limits, client IP detection, list cache |
| `test_settings.py`, `test_admin_flag.py` | production settings and the admin flag |
| `test_api.py` | health and the public list |

CI runs the same checks, plus `manage.py check --deploy` with production settings.

## Dependencies

Managed with uv. Add a package with `uv add <name>` and commit the updated `uv.lock`. Do not commit a `.venv`.

## More

- [Root README](../README.md): the project overview
- [docs/slo.md](../docs/slo.md) and [docs/runbooks/](../docs/runbooks/): service levels and incident runbooks
- [docs/deploy.md](../docs/deploy.md): deploy and rollback
