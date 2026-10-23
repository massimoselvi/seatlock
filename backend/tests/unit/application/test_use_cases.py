"""Use cases run against in-memory fakes: no database, no HTTP, no Django app loading."""

import pytest

from application.workshops.services import CancelRegistration, PromoteWaitlist, RegisterForWorkshop
from domain.workshops.entities import RegistrationStatus, Workshop
from domain.workshops.exceptions import RegistrationNotFound, WorkshopNotFound

from .fakes import FakeUnitOfWork, RecordingCache, RecordingNotifier, RecordingQueue

Status = RegistrationStatus


class World:
    """One workshop with the three use cases wired to fakes."""

    def __init__(self, capacity: int = 1) -> None:
        self.uow = FakeUnitOfWork()
        self.uow.store.workshops[1] = Workshop(id=1, title="Async Python", capacity=capacity)
        self.cache = RecordingCache()
        self.queue = RecordingQueue()
        self.notifier = RecordingNotifier(self.uow)
        self.register = RegisterForWorkshop(self.uow, self.cache)
        self.cancel = CancelRegistration(self.uow, self.cache, self.queue)
        self.promote = PromoteWaitlist(self.uow, self.cache, self.notifier)

    def sign_up(self, user_id: int):
        return self.register.execute(user_id=user_id, workshop_id=1)


def test_seats_fill_then_waitlist():
    world = World(capacity=2)
    statuses = [world.sign_up(user).status for user in (1, 2, 3)]
    assert statuses == [Status.CONFIRMED, Status.CONFIRMED, Status.WAITLISTED]


def test_register_is_idempotent():
    world = World()
    first, second = world.sign_up(1), world.sign_up(1)
    assert first.id == second.id
    assert len(world.uow.store.registrations) == 1


def test_unknown_workshop_raises_and_changes_nothing():
    world = World()
    with pytest.raises(WorkshopNotFound):
        world.register.execute(user_id=1, workshop_id=99)
    assert world.cache.invalidations == 0


def test_register_invalidates_the_cache_after_commit():
    world = World()
    world.sign_up(1)
    assert world.cache.invalidations == 1


def test_cancelling_a_confirmed_seat_queues_a_promotion():
    world = World()
    seat = world.sign_up(1)

    world.cancel.execute(user_id=1, registration_id=seat.id)

    assert world.queue.enqueued == [1]


def test_cancelling_a_waitlisted_registration_queues_nothing():
    world = World()
    world.sign_up(1)
    waiting = world.sign_up(2)

    world.cancel.execute(user_id=2, registration_id=waiting.id)

    assert world.queue.enqueued == []


def test_cancelling_twice_is_harmless():
    world = World()
    seat = world.sign_up(1)
    world.cancel.execute(user_id=1, registration_id=seat.id)
    invalidations = world.cache.invalidations

    again = world.cancel.execute(user_id=1, registration_id=seat.id)

    assert again.status == Status.CANCELLED
    assert world.queue.enqueued == [1]
    assert world.cache.invalidations == invalidations


def test_cannot_cancel_someone_elses_registration():
    world = World()
    seat = world.sign_up(1)
    with pytest.raises(RegistrationNotFound):
        world.cancel.execute(user_id=2, registration_id=seat.id)
    assert world.uow.store.registrations[0].status == Status.CONFIRMED


def test_promotion_goes_to_the_oldest_waiting_user_and_notifies_them():
    world = World()
    first = world.sign_up(1)
    world.sign_up(2)
    world.sign_up(3)
    world.cancel.execute(user_id=1, registration_id=first.id)

    promoted = world.promote.execute(workshop_id=1)

    by_user = {r.user_id: r.status for r in world.uow.store.registrations}
    assert promoted == 1
    assert by_user == {1: Status.CANCELLED, 2: Status.CONFIRMED, 3: Status.WAITLISTED}
    assert world.notifier.notified == [2]


def test_notifications_are_sent_after_the_transaction_closes():
    world = World()
    first = world.sign_up(1)
    world.sign_up(2)
    world.cancel.execute(user_id=1, registration_id=first.id)

    world.promote.execute(workshop_id=1)

    assert world.notifier.saw_open_transaction is False


def test_promotion_does_nothing_when_the_workshop_is_full():
    world = World()
    world.sign_up(1)
    world.sign_up(2)

    assert world.promote.execute(workshop_id=1) == 0
    assert world.notifier.notified == []


def test_a_failure_rolls_back_and_skips_every_side_effect():
    world = World()
    world.sign_up(1)
    invalidations = world.cache.invalidations

    def boom(registration):
        raise RuntimeError("database went away")

    world.uow.registrations.add = boom
    with pytest.raises(RuntimeError):
        world.sign_up(2)

    assert len(world.uow.store.registrations) == 1
    assert world.cache.invalidations == invalidations


def test_seat_counts_are_only_read_under_the_workshop_lock():
    """The fake asserts this on every count. A use case that skips the lock fails here."""
    world = World(capacity=3)
    for user in (1, 2, 3, 4):
        world.sign_up(user)
    first = world.uow.store.registrations[0]
    world.cancel.execute(user_id=first.user_id, registration_id=first.id)
    world.promote.execute(workshop_id=1)


def test_newcomer_does_not_take_a_seat_freed_before_the_promotion_runs():
    world = World(capacity=1)
    first = world.sign_up(1)
    assert world.sign_up(2).status == Status.WAITLISTED
    world.cancel.execute(user_id=1, registration_id=first.id)  # promotion is only queued

    assert world.sign_up(3).status == Status.WAITLISTED
    world.promote.execute(workshop_id=1)
    statuses = {r.user_id: r.status for r in world.uow.store.registrations}
    assert statuses[2] == Status.CONFIRMED
    assert statuses[3] == Status.WAITLISTED


def test_cannot_register_once_the_workshop_has_started():
    from datetime import UTC, datetime, timedelta

    from domain.workshops.exceptions import WorkshopClosed

    now = datetime(2026, 11, 1, 10, tzinfo=UTC)
    world = World()
    world.uow.store.workshops[1] = Workshop(id=1, title="t", capacity=1, starts_at=now)
    world.register = RegisterForWorkshop(world.uow, world.cache, clock=lambda: now + timedelta(1))
    with pytest.raises(WorkshopClosed):
        world.sign_up(1)
    assert world.uow.store.registrations == []
