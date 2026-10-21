"""Seat rules as plain functions. Standard library only: no Django, no database.

`services.py` loads the rows, calls these functions to decide, then saves. That split is the
whole experiment: the decisions can be tested without a database, and the locking and
transactions stay in the one place that talks to PostgreSQL.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum


class RegistrationStatus(StrEnum):
    CONFIRMED = "confirmed"
    WAITLISTED = "waitlisted"
    CANCELLED = "cancelled"


ACTIVE_STATUSES = (RegistrationStatus.CONFIRMED, RegistrationStatus.WAITLISTED)


class InvalidStatusTransition(Exception):
    pass


def free_seats(capacity: int, confirmed: int) -> int:
    return max(capacity - confirmed, 0)


def status_for_new_registration(capacity: int, confirmed: int) -> RegistrationStatus:
    """A seat is confirmed while there is room, otherwise the user joins the waitlist."""
    if free_seats(capacity, confirmed) > 0:
        return RegistrationStatus.CONFIRMED
    return RegistrationStatus.WAITLISTED


@dataclass(frozen=True)
class Cancellation:
    status: RegistrationStatus
    changed: bool  # False when it was already cancelled
    freed_seat: bool  # True when a confirmed seat opened up


def cancel(status: RegistrationStatus) -> Cancellation:
    if status == RegistrationStatus.CANCELLED:
        return Cancellation(status, changed=False, freed_seat=False)
    return Cancellation(
        RegistrationStatus.CANCELLED,
        changed=True,
        freed_seat=status == RegistrationStatus.CONFIRMED,
    )


def promote(status: RegistrationStatus) -> RegistrationStatus:
    if status != RegistrationStatus.WAITLISTED:
        raise InvalidStatusTransition(f"Cannot promote a {status} registration.")
    return RegistrationStatus.CONFIRMED


def select_for_promotion[T](capacity: int, confirmed: int, waitlist: Sequence[T]) -> list[T]:
    """Pick who gets the free seats. The waitlist must be ordered oldest first."""
    return list(waitlist[: free_seats(capacity, confirmed)])
