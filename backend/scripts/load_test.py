"""Load test: seat allocation under concurrent HTTP load, against a real gunicorn and PostgreSQL.

Run it inside the web container, so it can reach the database and Redis:

    docker compose exec -T web python scripts/load_test.py

It starts its own gunicorn on a free port, creates throwaway users and workshops, fires requests
that all leave at the same moment, then checks the invariants in the database. Exit code 0 means
every check passed. The data it created is deleted at the end, unless --keep is given.

Scenarios:
  A. last seat      N users register together for S seats. Expect S confirmed, N - S waitlisted.
  B. idempotency    Each user sends the same register request several times at once. Expect one
                    active registration per user and the same registration id in every answer.
  C. cancel storm   Every confirmed user cancels together. The Celery worker promotes the oldest
                    waitlisted users. Expect S confirmed again and the right people promoted.

A sampler thread reads the confirmed count straight from the database during A and C. A value
above the capacity means a seat was sold twice.
"""

import argparse
import json
import os
import secrets
import socket
import statistics
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

PREFIX = "loadtest"
SETTLE_SECONDS = 30


@dataclass
class Shot:
    status: int
    ms: float
    body: dict | None = None


@dataclass
class Report:
    name: str
    shots: list[Shot] = field(default_factory=list)
    checks: list[tuple[str, bool, str]] = field(default_factory=list)
    seconds: float = 0.0
    max_confirmed_seen: int | None = None

    def check(self, label: str, ok: bool, detail: str = "") -> None:
        self.checks.append((label, ok, detail))

    @property
    def passed(self) -> bool:
        return all(ok for _, ok, _ in self.checks)


def percentile(values: list[float], pct: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round(pct / 100 * (len(ordered) - 1)))]


def post(base: str, path: str, token: str) -> Shot:
    request = urllib.request.Request(
        f"{base}{path}", method="POST", headers={"Authorization": f"Token {token}"}
    )
    start = time.perf_counter()
    status, body = 0, None
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            status, body = response.status, json.load(response)
    except urllib.error.HTTPError as error:
        status = error.code
    except OSError:
        status = 0  # connection refused or timed out
    return Shot(status, (time.perf_counter() - start) * 1000, body)


def fire(base: str, jobs: list[tuple[str, str]]) -> tuple[list[Shot], float]:
    """Start one thread per job, hold them at a gate, release them all at once."""
    gate = threading.Event()

    def run(job: tuple[str, str]) -> Shot:
        gate.wait()
        return post(base, *job)

    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        futures = [pool.submit(run, job) for job in jobs]
        time.sleep(0.5)  # let every thread reach the gate
        start = time.perf_counter()
        gate.set()
        shots = [future.result() for future in futures]
    return shots, time.perf_counter() - start


class Sampler(threading.Thread):
    """Reads the confirmed count from the database in a loop and keeps the maximum."""

    def __init__(self, workshop_id: int) -> None:
        super().__init__(daemon=True)
        self.workshop_id = workshop_id
        self.maximum = 0
        self.stop_flag = threading.Event()

    def run(self) -> None:
        from django.db import connection

        from infrastructure.db.models import Registration

        while not self.stop_flag.is_set():
            count = Registration.objects.filter(
                workshop_id=self.workshop_id, status="confirmed"
            ).count()
            self.maximum = max(self.maximum, count)
            time.sleep(0.003)
        connection.close()

    def finish(self) -> int:
        self.stop_flag.set()
        self.join(timeout=5)
        return self.maximum


def make_users(label: str, count: int) -> list[tuple[int, str]]:
    """Create users with tokens. Returns (user id, token). No password hashing, so it is quick."""
    from django.contrib.auth import get_user_model
    from rest_framework.authtoken.models import Token

    user_model = get_user_model()
    run = secrets.token_hex(3)
    users = user_model.objects.bulk_create(
        [
            user_model(username=f"{PREFIX}-{label}-{run}-{i}", email=f"{PREFIX}{i}@example.com")
            for i in range(count)
        ]
    )
    tokens = Token.objects.bulk_create(
        [Token(user=user, key=secrets.token_hex(20)) for user in users]
    )
    return [(token.user_id, token.key) for token in tokens]


def make_workshop(label: str, capacity: int):
    from django.utils import timezone

    from infrastructure.db.models import Workshop

    return Workshop.objects.create(
        title=f"[{PREFIX}] {label}",
        starts_at=timezone.now() + timezone.timedelta(days=1),
        capacity=capacity,
    )


def counts(workshop_id: int) -> dict[str, int]:
    from infrastructure.db.models import Registration

    rows = Registration.objects.filter(workshop_id=workshop_id)
    return {
        status: rows.filter(status=status).count()
        for status in ("confirmed", "waitlisted", "cancelled")
    }


def summarize_http(report: Report, expected_status: int = 200) -> None:
    bad = [shot.status for shot in report.shots if shot.status != expected_status]
    report.check(
        f"all {len(report.shots)} requests answered {expected_status}",
        not bad,
        f"unexpected statuses: {sorted(set(bad))}" if bad else "",
    )


def scenario_last_seat(base: str, users: int, seats: int) -> Report:
    report = Report("A. last seat")
    workshop = make_workshop("A last seat", seats)
    accounts = make_users("a", users)
    sampler = Sampler(workshop.pk)
    sampler.start()
    report.shots, report.seconds = fire(
        base, [(f"/api/workshops/{workshop.pk}/register/", token) for _, token in accounts]
    )
    report.max_confirmed_seen = sampler.finish()

    from infrastructure.db.models import Registration

    done = counts(workshop.pk)
    per_user = Registration.objects.filter(workshop=workshop).values("user").distinct().count()
    answered_confirmed = sum(1 for s in report.shots if s.body and s.body["status"] == "confirmed")
    summarize_http(report)
    report.check(
        f"exactly {seats} confirmed in the database", done["confirmed"] == seats, str(done)
    )
    report.check(
        f"exactly {users - seats} waitlisted in the database",
        done["waitlisted"] == users - seats,
        str(done),
    )
    report.check(
        "one registration per user", per_user == users, f"{per_user} users, {users} expected"
    )
    report.check(
        f"clients were told 'confirmed' exactly {seats} times",
        answered_confirmed == seats,
        f"{answered_confirmed} answers said confirmed",
    )
    report.check(
        f"confirmed never exceeded {seats} while sampling the database",
        report.max_confirmed_seen <= seats,
        f"highest value seen: {report.max_confirmed_seen}",
    )
    return report


def scenario_idempotency(base: str, users: int, repeats: int, seats: int) -> Report:
    report = Report("B. idempotency")
    workshop = make_workshop("B idempotency", seats)
    accounts = make_users("b", users)
    owners = [index for index in range(users) for _ in range(repeats)]
    jobs = [(f"/api/workshops/{workshop.pk}/register/", accounts[index][1]) for index in owners]
    report.shots, report.seconds = fire(base, jobs)

    from infrastructure.db.models import Registration

    summarize_http(report)
    active = Registration.objects.filter(workshop=workshop).exclude(status="cancelled")
    report.check(
        "one active registration per user",
        active.count() == users and active.values("user").distinct().count() == users,
        f"{active.count()} active rows for {users} users",
    )
    ids_per_user: dict[int, set[int]] = {}
    for owner, shot in zip(owners, report.shots, strict=True):
        if shot.body:
            ids_per_user.setdefault(owner, set()).add(shot.body["id"])
    same = all(len(ids) == 1 for ids in ids_per_user.values())
    report.check("every repeat returned the same registration id", same)
    done = counts(workshop.pk)
    report.check(
        f"{min(seats, users)} confirmed",
        done["confirmed"] == min(seats, users),
        str(done),
    )
    return report


def scenario_cancel_storm(base: str, seats: int, waiting: int) -> Report:
    report = Report("C. cancel storm and promotion")
    workshop = make_workshop("C cancel storm", seats)
    accounts = make_users("c", seats + waiting)

    from infrastructure.db.models import Registration

    rows = Registration.objects.bulk_create(
        [
            Registration(
                workshop=workshop,
                user_id=user_id,
                status="confirmed" if i < seats else "waitlisted",
            )
            for i, (user_id, _) in enumerate(accounts)
        ]
    )
    confirmed_rows = rows[:seats]
    oldest_waiting = {row.pk for row in rows[seats : seats * 2]}
    tokens = dict(accounts)

    sampler = Sampler(workshop.pk)
    sampler.start()
    report.shots, report.seconds = fire(
        base,
        [(f"/api/registrations/{row.pk}/cancel/", tokens[row.user_id]) for row in confirmed_rows],
    )
    deadline = time.monotonic() + SETTLE_SECONDS
    while time.monotonic() < deadline and counts(workshop.pk)["confirmed"] < seats:
        time.sleep(0.2)
    time.sleep(1)  # a late, wrong promotion would show up here
    report.max_confirmed_seen = sampler.finish()

    done = counts(workshop.pk)
    promoted = set(
        Registration.objects.filter(workshop=workshop, status="confirmed")
        .exclude(pk__in=[row.pk for row in confirmed_rows])
        .values_list("pk", flat=True)
    )
    summarize_http(report)
    report.check(f"{seats} cancelled", done["cancelled"] == seats, str(done))
    report.check(
        f"the worker promoted waitlisted users until {seats} seats were confirmed again",
        done["confirmed"] == seats,
        f"{done}. If this fails, check that the worker container is running.",
    )
    report.check(
        "the oldest waitlisted users were promoted, in order of arrival",
        promoted == oldest_waiting,
        f"promoted {len(promoted)}, expected the {len(oldest_waiting)} oldest",
    )
    report.check(
        f"confirmed never exceeded {seats} while sampling the database",
        report.max_confirmed_seen <= seats,
        f"highest value seen: {report.max_confirmed_seen}",
    )
    return report


def cleanup() -> None:
    from django.contrib.auth import get_user_model

    from infrastructure.db.models import Workshop

    Workshop.objects.filter(title__startswith=f"[{PREFIX}]").delete()
    get_user_model().objects.filter(username__startswith=f"{PREFIX}-").delete()


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def start_server(workers: int, threads: int) -> tuple[subprocess.Popen, str]:
    port = free_port()
    env = {**os.environ, "DEBUG": "false", "SECRET_KEY": secrets.token_urlsafe(50)}
    env["ALLOWED_HOSTS"] = "127.0.0.1,localhost"
    process = subprocess.Popen(
        [
            "gunicorn", "config.wsgi", "--bind", f"127.0.0.1:{port}",
            "--workers", str(workers), "--threads", str(threads), "--log-level", "warning",
            "--no-control-socket",
        ],
        env=env,
    )  # fmt: skip
    base = f"http://127.0.0.1:{port}"
    for _ in range(100):
        try:
            urllib.request.urlopen(f"{base}/api/health/", timeout=1).close()
            return process, base
        except OSError:
            time.sleep(0.1)
    process.terminate()
    raise SystemExit("gunicorn did not start")


def print_report(report: Report) -> None:
    latencies = [shot.ms for shot in report.shots]
    rate = len(report.shots) / report.seconds if report.seconds else 0
    print(f"\n{report.name}")
    print(
        f"  {len(report.shots)} requests in {report.seconds:.2f} s ({rate:.0f} req/s)"
        f"  latency p50 {statistics.median(latencies):.0f} ms,"
        f" p95 {percentile(latencies, 95):.0f} ms, p99 {percentile(latencies, 99):.0f} ms,"
        f" max {max(latencies):.0f} ms"
    )
    for label, ok, detail in report.checks:
        print(
            f"  {'PASS' if ok else 'FAIL'}  {label}"
            + (f"  [{detail}]" if detail and not ok else "")
        )


def to_json(report: Report) -> dict:
    latencies = [shot.ms for shot in report.shots]
    return {
        "scenario": report.name,
        "requests": len(report.shots),
        "seconds": round(report.seconds, 3),
        "requests_per_second": round(len(report.shots) / report.seconds, 1)
        if report.seconds
        else 0,
        "latency_ms": {
            "p50": round(statistics.median(latencies)),
            "p95": round(percentile(latencies, 95)),
            "p99": round(percentile(latencies, 99)),
            "max": round(max(latencies)),
        },
        "status_codes": {
            str(c): sum(1 for s in report.shots if s.status == c)
            for c in sorted({s.status for s in report.shots})
        },
        "max_confirmed_seen": report.max_confirmed_seen,
        "checks": [
            {"check": label, "passed": ok, "detail": detail} for label, ok, detail in report.checks
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--users", type=int, default=200, help="users in scenario A (default 200)")
    parser.add_argument("--seats", type=int, default=10, help="seats per workshop (default 10)")
    parser.add_argument("--repeats", type=int, default=5, help="identical requests per user in B")
    parser.add_argument("--workers", type=int, default=4, help="gunicorn workers (default 4)")
    parser.add_argument("--threads", type=int, default=1, help="threads per worker (default 1)")
    parser.add_argument("--base-url", help="use a running server instead of starting gunicorn")
    parser.add_argument("--out", help="write the results as JSON to this file")
    parser.add_argument("--keep", action="store_true", help="do not delete the test data")
    args = parser.parse_args()

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    sys.path.insert(0, os.getcwd())
    import django

    django.setup()
    cleanup()  # a previous run may have been interrupted

    process, base = (
        (None, args.base_url) if args.base_url else start_server(args.workers, args.threads)
    )
    print(
        f"target {base}"
        + ("" if args.base_url else f" (gunicorn, {args.workers} workers x {args.threads} threads)")
    )
    reports: list[Report] = []
    try:
        reports.append(scenario_last_seat(base, args.users, args.seats))
        reports.append(scenario_idempotency(base, 20, args.repeats, args.seats))
        reports.append(scenario_cancel_storm(base, args.seats, args.seats * 3))
    finally:
        if process:
            process.terminate()
            process.wait(timeout=10)
        if not args.keep:
            cleanup()

    for report in reports:
        print_report(report)
    ok = all(report.passed for report in reports)
    print(f"\n{'ALL CHECKS PASSED' if ok else 'CHECKS FAILED'}")
    if args.out:
        with open(args.out, "w") as handle:
            json.dump(
                {
                    "server": {"workers": args.workers, "threads": args.threads},
                    "users": args.users,
                    "seats": args.seats,
                    "passed": ok,
                    "scenarios": [to_json(r) for r in reports],
                },
                handle,
                indent=2,
            )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
