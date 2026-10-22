# Load test: no overselling under concurrent load

The claim of this project is that a seat is never sold twice. The concurrency test in `tests/integration` proves it with 20 threads inside the test process. This load test proves it over real HTTP, against a real gunicorn, PostgreSQL, Redis and a Celery worker.

## Result

| | With the row lock (real code) | Without the lock (control experiment) |
|---|---|---|
| Runs | 8 | 6 |
| Runs where every check passed | **8 of 8** | **0 of 6** |
| 200 users, 10 seats: confirmed seats | **10** in every run | **24, 15, 18** with 4 workers x 8 threads |
| Highest confirmed count seen by a database sampler | 10 | 24, 15, 18 |
| Duplicate registrations from retries | none | none: the unique index rejected the loser with a `500` |
| HTTP answers other than `200` | 0 of 2,480 | 0 to 10 per run, all in scenario B |

In short: 200 people press "register" at the same moment for 10 seats. With the lock, exactly 10 are confirmed and 190 are waitlisted, every time. Remove the lock and up to 24 people get a seat.

## What it tests

The script is [backend/scripts/load_test.py](../backend/scripts/load_test.py). It starts its own gunicorn, creates throwaway users and workshops, sends requests that all leave at the same moment, and then checks the database.

| Scenario | Load | What must hold |
|----------|------|----------------|
| **A. Last seat** | 200 users register at once for a 10-seat workshop | 10 confirmed and 190 waitlisted in the database. One registration per user. Exactly 10 clients were told "confirmed". |
| **B. Idempotency** | 20 users each send the same register request 5 times at once (100 requests) | One active registration per user. Every repeat returns the same registration id. |
| **C. Cancel storm** | All 10 confirmed users cancel at once, and the Celery worker promotes people from a waitlist of 30 | 10 cancelled. 10 confirmed again after promotion. The 10 **oldest** waitlisted users were the ones promoted. |

In A and C a sampler thread reads the confirmed count from PostgreSQL every 3 ms. A value above 10 at any moment means a seat was sold twice, even if it was fixed later.

How requests are sent:

- One thread per request. All threads wait at a gate, and the gate opens once. This gives the maximum overlap that one client can produce.
- Plain HTTP with the real token authentication, through the same URLs and middleware as the frontend.
- Each user has its own token, so the per-user throttle (10 per minute) does not interfere.

The server matches the production command in `infra/seatlock_infra/app_stack.py` (`gunicorn config.wsgi --workers 2` on 2 tasks):

| Configuration | Meaning |
|---------------|---------|
| `--workers 4 --threads 1` | Production-like: 4 worker processes, 4 requests in flight at most. |
| `--workers 4 --threads 8` | Harsher: up to 32 requests in flight, so more transactions fight for the lock. |

`DEBUG` is off for the gunicorn under test, as in production. The Celery worker is the one from `docker compose`.

## Results with the lock

8 runs on the real code: 4 with 4x1 and 4 with 4x8. Every check passed in every run.

| | Scenario A | Scenario B | Scenario C |
|---|---|---|---|
| Requests per run | 200 | 100 | 10 |
| HTTP status | 200 x 200 | 200 x 100 | 200 x 10 |
| Confirmed in the database | 10 | 10 | 10 (after promotion) |
| Highest confirmed count sampled | 10 | n/a | 10 |

Example output of one run (4 workers x 8 threads):

```
A. last seat
  200 requests in 3.18 s (63 req/s)  latency p50 1961 ms, p95 3041 ms, p99 3119 ms, max 3137 ms
  PASS  all 200 requests answered 200
  PASS  exactly 10 confirmed in the database
  PASS  exactly 190 waitlisted in the database
  PASS  one registration per user
  PASS  clients were told 'confirmed' exactly 10 times
  PASS  confirmed never exceeded 10 while sampling the database
B. idempotency
  PASS  one active registration per user
  PASS  every repeat returned the same registration id
C. cancel storm and promotion
  PASS  the worker promoted waitlisted users until 10 seats were confirmed again
  PASS  the oldest waitlisted users were promoted, in order of arrival
ALL CHECKS PASSED
```

### Timings (indicative only)

| Metric, scenario A | Range over the 8 runs |
|---|---|
| Throughput | 34 to 190 requests per second |
| Latency p50 | 0.5 s to 3.9 s |
| Latency p95 | 1.0 s to 5.5 s |

These numbers vary by about a factor of 5 between runs. They are **not** a capacity measurement. 200 clients arrive in one instant, so most of the latency is waiting in the queue for one of 4 to 32 request slots. The load generator also runs in the same container and uses the same CPUs as the server. Use the timings to spot a regression on the same machine, not to size production.

## Control experiment: remove the lock

A test that cannot fail proves nothing. The same script ran against code with `select_for_update()` removed from `DjangoWorkshopRepository.lock` (a temporary edit, reverted after the runs). Every run failed.

| Configuration | Run | Scenario A: confirmed for 10 seats | Scenario B: confirmed for 10 seats | Scenario B: `500` answers |
|---|---|---:|---:|---:|
| 4 x 1 | 1 | 10 | **12** | 0 |
| 4 x 1 | 2 | 10 | 10 | **2** |
| 4 x 1 | 3 | 10 | 10 | **1** |
| 4 x 8 | 1 | **24** | **13** | **10** |
| 4 x 8 | 2 | **15** | **15** | **7** |
| 4 x 8 | 3 | **18** | **15** | **9** |

What this shows:

1. **The lock is what protects the seats.** With 32 requests in flight, the workshop was oversold by up to 2.4 times in every run. Both the database sampler and the clients' own answers (24 clients told "confirmed") saw it.
2. **Even a small amount of parallelism is enough.** With only 4 requests in flight, a workshop was still oversold in one run.
3. **The database constraint is a real second line of defence.** Without the lock, two identical requests from one user raced, and the unique index `one_active_registration_per_user` rejected the loser. The user got a `500` instead of a clean answer. With the lock, the second request waits, finds the first registration and returns it with `200`. That is why scenario B passes.
4. **The constraint does not protect seat counts.** Only the lock does. Nothing in the schema limits how many `confirmed` rows a workshop may have.

## How to run it

The stack must be up (`docker compose up`), including the worker, because scenario C needs it.

```bash
docker compose exec -T web python scripts/load_test.py
```

| Option | Default | Meaning |
|--------|---------|---------|
| `--users` | 200 | Users in scenario A |
| `--seats` | 10 | Seats per workshop |
| `--repeats` | 5 | Identical requests per user in scenario B |
| `--workers`, `--threads` | 4, 1 | gunicorn configuration |
| `--base-url` | none | Test a server that is already running, instead of starting gunicorn |
| `--out FILE` | none | Also write the results as JSON |
| `--keep` | off | Keep the test data |

- The exit code is 0 only if every check passed, so it can gate a pipeline.
- Test data is easy to recognize (`[loadtest]` workshops and `loadtest-` users) and is deleted at the end. A run that was interrupted is cleaned up at the start of the next one. It is safe on a development database. Do not point it at production.
- Keep the Postgres limit in mind: each gunicorn worker or thread can hold one connection, and `max_connections` is 100 in the compose database.

To repeat the control experiment, remove `.select_for_update()` in `infrastructure/db/repositories.py`, run the script with `--workers 4 --threads 8`, and revert the edit.

## Continuous integration

The workflow [.github/workflows/load-test.yml](../.github/workflows/load-test.yml) runs the same script in GitHub Actions, so a change to the lock fails a build.

| | |
|---|---|
| **When** | By hand (`workflow_dispatch`, with inputs for users and seats), and on pull requests that touch `backend/domain`, `backend/application`, `backend/infrastructure`, `backend/config/settings.py`, the script or the workflow. |
| **Where** | A GitHub runner with PostgreSQL 17 and Redis as service containers, and a Celery worker started in the background. The worker is needed for scenario C. |
| **Matrix** | Two jobs: 4 workers x 1 thread (production-like) and 4 workers x 8 threads (up to 32 requests at once). |
| **What fails the build** | Any broken invariant. Timings never fail it, so a slow runner cannot turn the job red. |
| **Output** | A table in the job summary, and the JSON result and the worker log as an artifact. |

**The control job.** A test that cannot fail proves nothing, so the workflow has a second job, `control-without-lock`. It removes `select_for_update()` from `DjangoWorkshopRepository.lock` and expects the load test to fail. It allows 3 attempts, because the race is likely but not certain, and it fails the build if the test passes 3 times without the lock. It runs only when you start the workflow by hand and tick `control`, so it does not slow pull requests. Run it after you change the script.

The workflow was checked locally before the first run on GitHub: `act` parsed it and expanded the matrix, and a harness ran the job steps against a fresh database and an isolated Redis. In that run the real code passed all checks, and the lock-free code confirmed 29 people for 10 seats and failed.

The job is not a required status check. A required check must report on every pull request, and a path-filtered workflow does not run on pull requests that touch other files. Making it required needs a small always-on wrapper job.

## Limits of this test

- **One machine.** Docker Desktop on a laptop (10 CPUs, 16 GB for the VM), PostgreSQL 17, one Celery worker. The production target is two ECS tasks. The lock lives in PostgreSQL, so more tasks queue on the same lock, but this test did not run more than one gunicorn.
- **One hot workshop.** All requests hit one workshop row. That is the worst case for the lock and the case that matters for "the last seat". It does not model many workshops at once.
- **Burst, not sustained load.** It checks correctness in a spike. It does not check behavior over minutes or hours.
- **Direct database access.** The script creates users and reads results from the database. It does not go through a load balancer, a CDN or a connection pooler. A pooler in transaction or statement mode could break row locks (see the [oversold runbook](runbooks/seats-oversold.md)). That deployment must be tested separately.
- **Only seat-changing endpoints.** The public list, the organizer endpoints and sign-up are not loaded here.

## Incidental finding

gunicorn 26 tries to open a control socket in `$HOME/.gunicorn`. The container user `app` has no home directory, so each start logs:

```
[ERROR] Control server error: [Errno 13] Permission denied: '/home/app'
```

It is not fatal, and the server runs normally. The load test passes `--no-control-socket` to avoid the noise. The `Dockerfile` command and `WEB_COMMAND` in the CDK stack start gunicorn as the same user, so production logs most likely show the same line. This was not checked on AWS. Adding `--no-control-socket` to both would remove it. It was not changed here.

## Ideas for later

- Run two gunicorn processes in two containers against one database, to test several tasks.
- Add a sustained scenario with many workshops and a mix of register and cancel calls.
