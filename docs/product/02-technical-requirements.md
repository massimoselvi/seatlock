# Technical Requirements Document

| | |
|---|---|
| Version | 1.0, issued 2026-10-23 |
| Owner | Massimo Selvi (tech lead) |
| Related | [PRD](01-prd.md), [Backend schema](05-backend-schema.md), [Architecture guide](../architecture.md), [ADRs](../architecture/adr/) |

Status: **Met** is verified by a test or a measurement. **Planned** names the issue. **Gap** is known and not planned.

## 1. Stack

| Part | Choice | Reason |
|------|--------|--------|
| Language, API | Python, Django 6.1, Django REST framework | Mature, the owner's primary stack |
| Database | PostgreSQL | Row locks and partial unique indexes |
| Queue, cache | Celery, Redis | Promotions and emails off the request path. One Redis for cache, throttling and the queue. |
| Frontend | Vue 3, Vite, TypeScript, pnpm, UnoCSS | [ADR 0006](../architecture/adr/0006-style-the-frontend-with-unocss.md) |
| Server | gunicorn behind an ALB and CloudFront | [ADR 0003](../architecture/adr/0003-target-aws-architecture.md) |
| Infrastructure | AWS CDK in Python (network, data, app, frontend stacks) | [ADR 0004](../architecture/adr/0004-infrastructure-as-code-with-aws-cdk.md) |
| Local | Docker Compose: db, redis, web, worker, frontend | One command to run it all |
| CI | GitHub Actions: `ci.yml`, `load-test.yml`, `architecture.yml` | |
| Packages | uv with `uv.lock`, pnpm with a lockfile | Reproducible |

## 2. Architecture requirements

| ID | Requirement | Status | Check |
|----|-------------|--------|-------|
| TR-A1 | Layers: domain, application, infrastructure, interface. Dependencies point inward. | Met | `tests/test_architecture.py` |
| TR-A2 | Domain and application import no Django, DRF or Celery. | Met | same test |
| TR-A3 | Seat rules are plain Python in `domain/`. Use cases are in `application/workshops/services.py`. | Met | `tests/unit` runs with no database |
| TR-A4 | Use cases are built only through `infrastructure/container.py`. Each call returns a fresh use case with its own unit of work. | Met | Review, `tests/unit/application` |
| TR-A5 | A new external dependency gets a port, an adapter and a recording fake. | Met | [Architecture guide](../architecture.md) |
| TR-A6 | The ORM status enum and the domain status enum agree. | Met | `tests/test_status_mapping.py` |

## 3. Concurrency and data requirements

| ID | Requirement | Status | Check |
|----|-------------|--------|-------|
| TR-C1 | Any change to seat counts runs in a use case that **locks the workshop row first** (`select_for_update` inside `transaction.atomic`) and reads counts after. | Met | `test_seat_counts_are_only_read_under_the_workshop_lock` |
| TR-C2 | Side effects (cache invalidation, Celery enqueue) run after commit. Email is sent after the `with` block closes. | Met | `test_notifications_are_sent_after_the_transaction_closes`, `test_cache_is_not_invalidated_on_rollback` |
| TR-C3 | A failed use case rolls back and runs no side effect. | Met | `test_a_failure_rolls_back_and_skips_every_side_effect` |
| TR-C4 | The database backs up the app: `capacity > 0`, one active registration per user and workshop. | Met | Migration `0001_initial` |
| TR-C5 | The real database lock is proved by a concurrent test and a load test. | Met | `test_concurrent_registrations_never_oversell`, `backend/scripts/load_test.py` |
| TR-C6 | The ORM app label stays `workshops` and the task name stays `workshops.tasks.promote_waitlist`. | Met | [Architecture guide](../architecture.md) |
| TR-C7 | The database constrains `status` to the three known values. | **Gap**, planned D2 | [Schema findings](05-backend-schema.md#5-findings) |
| TR-C8 | A lost email or a lost queued promotion is recovered by a sweep. | **Gap**, planned E1 | ADR 0005 gaps 3 and 4 |

## 4. Performance and capacity

| ID | Requirement | Target | Status |
|----|-------------|--------|--------|
| TR-P1 | p95 of `GET /api/workshops/` | under 300 ms | Planned: measured on AWS in the dry run (#43) |
| TR-P2 | p95 of register and cancel | under 800 ms | Same |
| TR-P3 | Promotion time from cancel to confirmation | p95 under 60 s | Alarm for queue backlog planned (#45) |
| TR-P4 | 200 simultaneous registrations for 10 seats | exactly 10 confirmed | Met, 8 of 8 runs |
| TR-P5 | The list is cached 30 s (`WORKSHOP_LIST_CACHE_SECONDS`) and the cache is dropped when seats change. Only the page number varies the key. | | Met, `tests/api/test_throttling_and_cache.py` |

## 5. Security requirements

| ID | Requirement | Status | Check or issue |
|----|-------------|--------|----------------|
| TR-S1 | Missing or default `SECRET_KEY` stops startup when `DEBUG` is off. | Met | `tests/config/test_settings.py` |
| TR-S2 | Production cookies are secure. HTTPS redirect and HSTS can be switched on, and the health path is exempt. | Met | same |
| TR-S3 | Rate limits: registration, login, auth 10 per minute. Anonymous 60, user 120. The client IP is read from the right end of `X-Forwarded-For` (`NUM_PROXIES`), so spoofing does not reset the limit. | Met | `test_spoofed_forwarded_for_prefix_does_not_reset_the_limit` |
| TR-S4 | `/admin` is not exposed on the public internet. | Met | `tests/config/test_admin_flag.py` |
| TR-S5 | The container runs as a non-root user. CI tokens have least privilege. | Met | #69, #70 |
| TR-S6 | Passwords use Django's validators and hashers. | Met | `test_signup_rejects_weak_password` |
| TR-S7 | The ALB accepts traffic only from CloudFront. | Met | #81 |
| TR-S8 | HTTPS between CloudFront and the ALB, and explicit `ALLOWED_HOSTS`. | Planned | #47, #48 |
| TR-S9 | Security headers and CSP. WAF in front of CloudFront. Redis auth token. | Planned | #58, #59, #60 |
| TR-S10 | Tokens expire and there is one per device. | Planned | #57 |
| TR-S11 | Access logs on the ALB and CloudFront. | Planned | #63 |
| TR-S12 | Actions pinned to commit SHAs. Dependabot. Compose ports bound to localhost. | Planned | #62, #61 |

## 6. Observability and operations

| ID | Requirement | Status |
|----|-------------|--------|
| TR-O1 | SLOs and alarms are defined in [slo.md](../slo.md) with a runbook for each page. | Met (documents) |
| TR-O2 | Alarm: oversold seats (check every 5 min, page). | Planned #46 |
| TR-O3 | Alarm: queue backlog above 100 for 10 min. | Planned #45 |
| TR-O4 | `GET /api/health/` for the load balancer. | Met |
| TR-O5 | Gunicorn logs go to stdout without startup noise. | Met, #80 |
| TR-O6 | The deploy guide has been run on a real account and then destroyed. | Planned #43 |
| TR-O7 | Every cloud resource has tags, including `DestroyBy`. A budget alarm exists. | Met in code (#81), not yet applied |

## 7. Quality gates

| ID | Gate | Status |
|----|------|--------|
| TR-Q1 | Backend: `ruff check`, `ruff format --check`, migrations check, pytest. | Met, 88 tests, 99% coverage |
| TR-Q2 | Frontend: `pnpm run ci` runs eslint, type-check, knip, vitest and build. | Met, 41 tests |
| TR-Q3 | Infra tests. | Met, 23 tests |
| TR-Q4 | Load test in CI on changes to domain, application or infrastructure. | Met (`load-test.yml`) |
| TR-Q5 | `main` changes only through a pull request with green checks. | Met |
| TR-Q6 | Tests that need PostgreSQL run in Docker. Unit and architecture tests need none (40 tests, about 0.1 s). | Met |

## 8. Interface requirements

| ID | Requirement |
|----|-------------|
| TR-I1 | JSON over HTTP under `/api/`. Authentication: `Authorization: Token <key>`. |
| TR-I2 | List responses are paginated, 20 per page. |
| TR-I3 | Errors use standard codes: 400 validation, 401 and 403 access, 404 unknown or not yours, 429 throttled. |
| TR-I4 | The frontend proxies `/api` to the backend, so it needs no CORS setup in development. |

Endpoints are listed in the [backend schema](05-backend-schema.md#6-api-surface).

## 9. Constraints

- C1. PostgreSQL must be real PostgreSQL, directly or through a pooler in session mode.
- C2. The repository is public: no secrets, no personal data.
- C3. Frontend colors come from tokens in `src/styles/theme.css`. Class names are complete static strings, so UnoCSS can scan them.
- C4. No Linux-built `.venv` or `node_modules` in the repository.

## 10. Traceability

| PRD | Technical requirements |
|-----|------------------------|
| FR-04, FR-05, FR-06 | TR-C1, TR-C4, TR-C5, TR-P4 |
| FR-07, FR-08, FR-09 | TR-C2, TR-C3, TR-C8 |
| FR-02, FR-03 | TR-S3, TR-S6, TR-S10 |
| FR-11 | TR-S4, TR-I1 |
| NFR-02, NFR-03 | TR-P1, TR-P2, TR-O1 to TR-O3 |
| NFR-04 | TR-S3 |
