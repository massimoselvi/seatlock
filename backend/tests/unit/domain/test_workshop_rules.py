"""Pure unit tests: no database, no Django, no fixtures."""

import pytest

from domain.workshops.entities import Registration, RegistrationStatus, Workshop
from domain.workshops.exceptions import InvalidStatusTransition, WorkshopClosed

Status = RegistrationStatus


def workshop(capacity: int = 2) -> Workshop:
    return Workshop(id=1, title="Async Python", capacity=capacity)


def registration(status: Status, user_id: int = 1) -> Registration:
    return Registration(workshop_id=1, user_id=user_id, status=status)


@pytest.mark.parametrize(
    ("confirmed", "expected"),
    [(0, Status.CONFIRMED), (1, Status.CONFIRMED), (2, Status.WAITLISTED), (3, Status.WAITLISTED)],
)
def test_new_registration_status_depends_on_free_seats(confirmed, expected):
    assert workshop(capacity=2).status_for_new_registration(confirmed) == expected


def test_free_seats_never_negative():
    assert workshop(capacity=2).free_seats(5) == 0


def test_cancelling_a_confirmed_seat_frees_it():
    reg = registration(Status.CONFIRMED)
    assert reg.cancel() is True
    assert reg.status == Status.CANCELLED


def test_cancelling_a_waitlisted_registration_frees_no_seat():
    reg = registration(Status.WAITLISTED)
    assert reg.cancel() is False
    assert reg.status == Status.CANCELLED


def test_cancelling_twice_changes_nothing():
    reg = registration(Status.CANCELLED)
    assert reg.cancel() is False


def test_promote_moves_waitlisted_to_confirmed():
    reg = registration(Status.WAITLISTED)
    reg.promote()
    assert reg.status == Status.CONFIRMED


@pytest.mark.parametrize("status", [Status.CONFIRMED, Status.CANCELLED])
def test_only_waitlisted_registrations_can_be_promoted(status):
    with pytest.raises(InvalidStatusTransition):
        registration(status).promote()


def test_promotion_fills_free_seats_oldest_first():
    queue = [registration(Status.WAITLISTED, user_id=i) for i in (10, 11, 12)]
    picked = workshop(capacity=3).select_for_promotion(confirmed=1, waitlist=queue)
    assert [r.user_id for r in picked] == [10, 11]


def test_no_promotion_when_full():
    queue = [registration(Status.WAITLISTED)]
    assert workshop(capacity=1).select_for_promotion(confirmed=1, waitlist=queue) == []


def test_newcomer_queues_while_anyone_waits_even_if_a_seat_is_free():
    assert workshop(capacity=2).status_for_new_registration(1, waitlisted=1) == Status.WAITLISTED


def test_workshop_closes_when_it_starts():
    from datetime import UTC, datetime, timedelta

    now = datetime(2026, 11, 1, 10, tzinfo=UTC)
    open_ws = Workshop(id=1, title="t", capacity=1, starts_at=now + timedelta(minutes=1))
    open_ws.ensure_open(now)
    with pytest.raises(WorkshopClosed):
        Workshop(id=1, title="t", capacity=1, starts_at=now).ensure_open(now)


def test_workshop_without_start_time_is_always_open():
    from datetime import UTC, datetime

    workshop().ensure_open(datetime.now(UTC))
