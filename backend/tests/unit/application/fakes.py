"""In-memory test doubles for the ports. They let use cases run with no Django and no database."""

import copy
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from application.workshops.interfaces import (
    PromotionNotifier,
    RegistrationRepository,
    UnitOfWork,
    WaitlistPromotionQueue,
    WorkshopListCache,
    WorkshopRepository,
)
from domain.workshops.entities import ACTIVE_STATUSES, Registration, RegistrationStatus, Workshop
from domain.workshops.exceptions import RegistrationNotFound, WorkshopNotFound


@dataclass
class Store:
    workshops: dict[int, Workshop] = field(default_factory=dict)
    registrations: list[Registration] = field(default_factory=list)
    next_id: int = 1


class FakeWorkshops(WorkshopRepository):
    def __init__(self, uow: "FakeUnitOfWork") -> None:
        self.uow = uow

    def lock(self, workshop_id: int) -> Workshop:
        try:
            workshop = self.uow.store.workshops[workshop_id]
        except KeyError:
            raise WorkshopNotFound(workshop_id) from None
        self.uow.locked.add(workshop_id)
        return workshop


class FakeRegistrations(RegistrationRepository):
    def __init__(self, uow: "FakeUnitOfWork") -> None:
        self.uow = uow

    @property
    def rows(self) -> list[Registration]:
        return self.uow.store.registrations

    def _require_lock(self, workshop_id: int) -> None:
        # The rule from ADR 0001, written as a test double: read seat counts only under the lock.
        assert workshop_id in self.uow.locked, "seat counts read without locking the workshop"

    def find_active(self, workshop_id: int, user_id: int) -> Registration | None:
        return next(
            (
                r
                for r in self.rows
                if r.workshop_id == workshop_id
                and r.user_id == user_id
                and r.status in ACTIVE_STATUSES
            ),
            None,
        )

    def count_confirmed(self, workshop_id: int) -> int:
        self._require_lock(workshop_id)
        return sum(
            r.workshop_id == workshop_id and r.status == RegistrationStatus.CONFIRMED
            for r in self.rows
        )

    def waitlist(self, workshop_id: int, limit: int) -> Sequence[Registration]:
        self._require_lock(workshop_id)
        waiting = [
            r
            for r in self.rows
            if r.workshop_id == workshop_id and r.status == RegistrationStatus.WAITLISTED
        ]
        return sorted(waiting, key=lambda r: r.id)[:limit]

    def get_for_user(self, registration_id: int, user_id: int) -> Registration:
        for r in self.rows:
            if r.id == registration_id and r.user_id == user_id:
                return r
        raise RegistrationNotFound(registration_id)

    def add(self, registration: Registration) -> Registration:
        registration.id = self.uow.store.next_id
        self.uow.store.next_id += 1
        registration.user_email = f"user{registration.user_id}@example.com"
        self.rows.append(registration)
        return registration

    def save(self, registration: Registration) -> None:
        pass  # entities are shared objects here


class FakeUnitOfWork(UnitOfWork):
    """Commit runs the on_commit callbacks. An exception restores the data and drops them."""

    def __init__(self, store: Store | None = None) -> None:
        self.store = store or Store()
        self.workshops = FakeWorkshops(self)
        self.registrations = FakeRegistrations(self)
        self.locked: set[int] = set()
        self.open = False
        self._callbacks: list[Callable[[], None]] = []
        self._snapshot: list[Registration] = []

    def __enter__(self):
        self.open = True
        self.locked = set()
        self._callbacks = []
        self._snapshot = copy.deepcopy(self.store.registrations)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.open = False
        if exc_type is not None:
            self.store.registrations[:] = self._snapshot
            return
        for callback in self._callbacks:
            callback()

    def on_commit(self, callback: Callable[[], None]) -> None:
        self._callbacks.append(callback)


class RecordingCache(WorkshopListCache):
    def __init__(self) -> None:
        self.invalidations = 0

    def invalidate(self) -> None:
        self.invalidations += 1


class RecordingQueue(WaitlistPromotionQueue):
    def __init__(self) -> None:
        self.enqueued: list[int] = []

    def enqueue(self, workshop_id: int) -> None:
        self.enqueued.append(workshop_id)


class RecordingNotifier(PromotionNotifier):
    def __init__(self, uow: FakeUnitOfWork) -> None:
        self.uow = uow
        self.notified: list[int] = []
        self.saw_open_transaction = False

    def notify(self, registration: Registration, workshop: Workshop) -> None:
        self.saw_open_transaction |= self.uow.open
        self.notified.append(registration.user_id)
