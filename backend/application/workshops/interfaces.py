"""Ports: what the use cases need from the outside world.

The application layer depends on these abstractions. The infrastructure layer implements them.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from typing import Self

from domain.workshops.entities import Registration, Workshop


class WorkshopRepository(ABC):
    @abstractmethod
    def lock(self, workshop_id: int) -> Workshop:
        """Load a workshop and lock it until the unit of work ends.

        Every change to seat counts must call this first. It is what stops two requests from
        taking the last seat together. Raises WorkshopNotFound.
        """

    @abstractmethod
    def with_waiting_and_free_seats(self) -> Sequence[int]:
        """Ids of workshops that have a waitlist and a free seat.

        A hint read, taken without the lock. It decides where to look, never what to change:
        the promotion locks the workshop and counts again.
        """


class RegistrationRepository(ABC):
    @abstractmethod
    def find_active(self, workshop_id: int, user_id: int) -> Registration | None: ...

    @abstractmethod
    def count_confirmed(self, workshop_id: int) -> int: ...

    @abstractmethod
    def count_waitlisted(self, workshop_id: int) -> int: ...

    @abstractmethod
    def waitlist(self, workshop_id: int, limit: int) -> Sequence[Registration]:
        """Waitlisted registrations, oldest first, at most `limit`."""

    @abstractmethod
    def get_for_user(self, registration_id: int, user_id: int) -> Registration:
        """Raises RegistrationNotFound, also when it belongs to another user."""

    @abstractmethod
    def add(self, registration: Registration) -> Registration: ...

    @abstractmethod
    def save(self, registration: Registration) -> None: ...


class UnitOfWork(ABC):
    """One transaction. Use it as a context manager: commit on success, roll back on error."""

    workshops: WorkshopRepository
    registrations: RegistrationRepository

    @abstractmethod
    def __enter__(self) -> Self: ...

    @abstractmethod
    def __exit__(self, exc_type, exc, tb) -> None: ...

    @abstractmethod
    def on_commit(self, callback: Callable[[], None]) -> None:
        """Run `callback` only if the transaction commits."""


class WaitlistPromotionQueue(ABC):
    @abstractmethod
    def enqueue(self, workshop_id: int) -> None: ...


class WorkshopListCache(ABC):
    @abstractmethod
    def invalidate(self) -> None: ...


class PromotionNotifier(ABC):
    @abstractmethod
    def notify(self, registration: Registration, workshop: Workshop) -> None: ...
