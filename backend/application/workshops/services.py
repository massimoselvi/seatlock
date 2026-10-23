"""Use cases. Each one is a workflow: load, apply a domain rule, save, trigger side effects.

No Django here. Everything the use cases touch arrives through the ports in `interfaces.py`.
"""

from collections.abc import Callable
from datetime import UTC, datetime

from domain.workshops.entities import Registration

from .dto import RegistrationResult
from .interfaces import (
    PromotionNotifier,
    UnitOfWork,
    WaitlistPromotionQueue,
    WorkshopListCache,
)


class RegisterForWorkshop:
    """Confirm a seat if one is free, otherwise join the waitlist. Idempotent."""

    def __init__(
        self,
        uow: UnitOfWork,
        list_cache: WorkshopListCache,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.uow = uow
        self.list_cache = list_cache
        self.clock = clock

    def execute(self, *, user_id: int, workshop_id: int) -> RegistrationResult:
        with self.uow:
            workshop = self.uow.workshops.lock(workshop_id)

            existing = self.uow.registrations.find_active(workshop.id, user_id)
            if existing:
                return RegistrationResult.from_entity(existing, workshop.title)

            workshop.ensure_open(self.clock())
            confirmed = self.uow.registrations.count_confirmed(workshop.id)
            waitlisted = self.uow.registrations.count_waitlisted(workshop.id)
            registration = self.uow.registrations.add(
                Registration(
                    workshop_id=workshop.id,
                    user_id=user_id,
                    status=workshop.status_for_new_registration(confirmed, waitlisted),
                )
            )
            self.uow.on_commit(self.list_cache.invalidate)
            return RegistrationResult.from_entity(registration, workshop.title)


class CancelRegistration:
    """Cancel a registration. A freed seat is offered to the waitlist after commit."""

    def __init__(
        self,
        uow: UnitOfWork,
        list_cache: WorkshopListCache,
        promotion_queue: WaitlistPromotionQueue,
    ) -> None:
        self.uow = uow
        self.list_cache = list_cache
        self.promotion_queue = promotion_queue

    def execute(self, *, user_id: int, registration_id: int) -> RegistrationResult:
        with self.uow:
            registration = self.uow.registrations.get_for_user(registration_id, user_id)
            workshop = self.uow.workshops.lock(registration.workshop_id)
            # Read again under the lock: another request may have cancelled it meanwhile.
            registration = self.uow.registrations.get_for_user(registration_id, user_id)

            if registration.is_cancelled:
                return RegistrationResult.from_entity(registration, workshop.title)

            freed_seat = registration.cancel()
            self.uow.registrations.save(registration)
            self.uow.on_commit(self.list_cache.invalidate)
            if freed_seat:
                self.uow.on_commit(lambda: self.promotion_queue.enqueue(workshop.id))
            return RegistrationResult.from_entity(registration, workshop.title)


class PromoteWaitlist:
    """Fill free seats from the waitlist, oldest first, then tell the people promoted."""

    def __init__(
        self, uow: UnitOfWork, list_cache: WorkshopListCache, notifier: PromotionNotifier
    ) -> None:
        self.uow = uow
        self.list_cache = list_cache
        self.notifier = notifier

    def execute(self, *, workshop_id: int) -> int:
        with self.uow:
            workshop = self.uow.workshops.lock(workshop_id)
            confirmed = self.uow.registrations.count_confirmed(workshop.id)
            free = workshop.free_seats(confirmed)
            candidates = self.uow.registrations.waitlist(workshop.id, free)
            promoted = workshop.select_for_promotion(confirmed, candidates)
            for registration in promoted:
                registration.promote()
                self.uow.registrations.save(registration)
            if promoted:
                self.uow.on_commit(self.list_cache.invalidate)

        # The transaction is committed here. Email is sent only for changes that are saved.
        for registration in promoted:
            self.notifier.notify(registration, workshop)
        return len(promoted)
