from concurrent.futures import ThreadPoolExecutor

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.utils import timezone

from workshops import services
from workshops.models import Registration, Workshop

Status = Registration.Status
User = get_user_model()


def make_workshop(capacity: int) -> Workshop:
    return Workshop.objects.create(
        title="Intro to Django", starts_at=timezone.now(), capacity=capacity
    )


def make_users(n: int):
    return [User.objects.create_user(f"u{i}", f"u{i}@example.com", "pw") for i in range(n)]


def count(workshop: Workshop, status: str) -> int:
    return workshop.registrations.filter(status=status).count()


@pytest.mark.django_db
def test_seats_fill_then_waitlist():
    workshop = make_workshop(capacity=2)
    statuses = [services.register(user=u, workshop_id=workshop.pk).status for u in make_users(3)]
    assert statuses == [Status.CONFIRMED, Status.CONFIRMED, Status.WAITLISTED]


@pytest.mark.django_db
def test_register_is_idempotent():
    workshop = make_workshop(capacity=1)
    (user,) = make_users(1)
    first = services.register(user=user, workshop_id=workshop.pk)
    second = services.register(user=user, workshop_id=workshop.pk)
    assert first.pk == second.pk
    assert workshop.registrations.count() == 1


@pytest.mark.django_db
def test_cancel_promotes_oldest_waitlisted(django_capture_on_commit_callbacks, mailoutbox):
    workshop = make_workshop(capacity=1)
    a, b, c = make_users(3)
    first = services.register(user=a, workshop_id=workshop.pk)
    services.register(user=b, workshop_id=workshop.pk)
    services.register(user=c, workshop_id=workshop.pk)

    with django_capture_on_commit_callbacks(execute=True):
        services.cancel(user=a, registration_id=first.pk)

    assert Registration.objects.get(user=b, workshop=workshop).status == Status.CONFIRMED
    assert Registration.objects.get(user=c, workshop=workshop).status == Status.WAITLISTED
    assert [m.to for m in mailoutbox] == [[b.email]]


@pytest.mark.django_db(transaction=True)
def test_concurrent_registrations_never_oversell():
    workshop = make_workshop(capacity=5)
    users = make_users(20)

    def attempt(user):
        try:
            return services.register(user=user, workshop_id=workshop.pk).status
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=20) as pool:
        list(pool.map(attempt, users))

    assert count(workshop, Status.CONFIRMED) == 5
    assert count(workshop, Status.WAITLISTED) == 15
