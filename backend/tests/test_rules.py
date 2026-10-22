"""Pure unit tests: no database, no fixtures."""

import pytest

from workshops import rules
from workshops.models import Registration

Status = rules.RegistrationStatus


@pytest.mark.parametrize(
    ("confirmed", "expected"),
    [(0, Status.CONFIRMED), (1, Status.CONFIRMED), (2, Status.WAITLISTED), (3, Status.WAITLISTED)],
)
def test_new_registration_status_depends_on_free_seats(confirmed, expected):
    assert rules.status_for_new_registration(capacity=2, confirmed=confirmed) == expected


def test_free_seats_never_negative():
    assert rules.free_seats(capacity=2, confirmed=5) == 0


def test_cancelling_a_confirmed_seat_frees_it():
    outcome = rules.cancel(Status.CONFIRMED)
    assert (outcome.status, outcome.changed, outcome.freed_seat) == (Status.CANCELLED, True, True)


def test_cancelling_a_waitlisted_registration_frees_no_seat():
    outcome = rules.cancel(Status.WAITLISTED)
    assert (outcome.status, outcome.changed, outcome.freed_seat) == (Status.CANCELLED, True, False)


def test_cancelling_twice_changes_nothing():
    outcome = rules.cancel(Status.CANCELLED)
    assert (outcome.changed, outcome.freed_seat) == (False, False)


def test_promote_moves_waitlisted_to_confirmed():
    assert rules.promote(Status.WAITLISTED) == Status.CONFIRMED


@pytest.mark.parametrize("status", [Status.CONFIRMED, Status.CANCELLED])
def test_only_waitlisted_can_be_promoted(status):
    with pytest.raises(rules.InvalidStatusTransition):
        rules.promote(status)


def test_promotion_fills_free_seats_oldest_first():
    assert rules.select_for_promotion(capacity=3, confirmed=1, waitlist=["a", "b", "c"]) == [
        "a",
        "b",
    ]


def test_no_promotion_when_full():
    assert rules.select_for_promotion(capacity=1, confirmed=1, waitlist=["a"]) == []


def test_rules_and_the_model_agree_on_status_values():
    """The enum is duplicated on purpose (rules.py has no Django). This catches drift."""
    assert {s.value for s in Status} == {s.value for s in Registration.Status}
    assert {s.value for s in rules.ACTIVE_STATUSES} == {
        s.value for s in Registration.ACTIVE_STATUSES
    }
