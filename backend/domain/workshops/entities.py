"""Business rules for seats. Plain Python: no Django, no database, no HTTP."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from .exceptions import InvalidStatusTransition


class RegistrationStatus(StrEnum):
    CONFIRMED = "confirmed"
    WAITLISTED = "waitlisted"
    CANCELLED = "cancelled"


ACTIVE_STATUSES = (RegistrationStatus.CONFIRMED, RegistrationStatus.WAITLISTED)


@dataclass
class Registration:
    workshop_id: int
    user_id: int
    status: RegistrationStatus
    user_email: str = ""
    id: int | None = None
    created_at: datetime | None = None

    @property
    def is_confirmed(self) -> bool:
        return self.status == RegistrationStatus.CONFIRMED

    @property
    def is_waitlisted(self) -> bool:
        return self.status == RegistrationStatus.WAITLISTED

    @property
    def is_cancelled(self) -> bool:
        return self.status == RegistrationStatus.CANCELLED

    def cancel(self) -> bool:
        """Cancel the registration. Returns True when a confirmed seat was freed."""
        if self.is_cancelled:
            return False
        freed_seat = self.is_confirmed
        self.status = RegistrationStatus.CANCELLED
        return freed_seat

    def promote(self) -> None:
        """Move a waitlisted registration to a confirmed seat."""
        if not self.is_waitlisted:
            raise InvalidStatusTransition(f"Cannot promote a {self.status} registration.")
        self.status = RegistrationStatus.CONFIRMED


@dataclass(frozen=True)
class Workshop:
    id: int
    title: str
    capacity: int

    def free_seats(self, confirmed: int) -> int:
        return max(self.capacity - confirmed, 0)

    def status_for_new_registration(self, confirmed: int) -> RegistrationStatus:
        """A seat is confirmed while there is room, otherwise the user joins the waitlist."""
        if self.free_seats(confirmed) > 0:
            return RegistrationStatus.CONFIRMED
        return RegistrationStatus.WAITLISTED

    def select_for_promotion(
        self, confirmed: int, waitlist: Sequence[Registration]
    ) -> list[Registration]:
        """Pick who gets the free seats. The waitlist must be ordered oldest first."""
        return list(waitlist[: self.free_seats(confirmed)])
