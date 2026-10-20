"""Seat allocation rules.

Every function that changes seat counts locks the Workshop row with
SELECT ... FOR UPDATE, so concurrent requests for the same workshop are
serialized and capacity can never be oversold.
"""

from django.db import transaction

from .models import Registration, Workshop

Status = Registration.Status


def _confirmed_count(workshop: Workshop) -> int:
    return workshop.registrations.filter(status=Status.CONFIRMED).count()


@transaction.atomic
def register(*, user, workshop_id: int) -> Registration:
    """Confirm a seat if one is free, otherwise join the waitlist. Idempotent."""
    workshop = Workshop.objects.select_for_update().get(pk=workshop_id)

    existing = Registration.objects.filter(
        workshop=workshop, user=user, status__in=Registration.ACTIVE_STATUSES
    ).first()
    if existing:
        return existing

    status = (
        Status.CONFIRMED if _confirmed_count(workshop) < workshop.capacity else Status.WAITLISTED
    )
    return Registration.objects.create(workshop=workshop, user=user, status=status)


@transaction.atomic
def cancel(*, user, registration_id: int) -> Registration:
    """Cancel a registration; a freed seat is offered to the waitlist after commit."""
    registration = Registration.objects.get(pk=registration_id, user=user)
    workshop = Workshop.objects.select_for_update().get(pk=registration.workshop_id)
    registration.refresh_from_db()

    if registration.status == Status.CANCELLED:
        return registration

    freed_seat = registration.status == Status.CONFIRMED
    registration.status = Status.CANCELLED
    registration.save(update_fields=["status"])

    if freed_seat:
        from .tasks import promote_waitlist

        transaction.on_commit(lambda: promote_waitlist.delay(workshop.pk))
    return registration


@transaction.atomic
def promote_waitlisted(*, workshop_id: int) -> list[Registration]:
    """Fill free seats from the waitlist, oldest first. Returns promoted rows."""
    workshop = Workshop.objects.select_for_update().get(pk=workshop_id)
    free = workshop.capacity - _confirmed_count(workshop)
    if free <= 0:
        return []

    queue = list(
        workshop.registrations.filter(status=Status.WAITLISTED).select_related("user")[:free]
    )
    for registration in queue:
        registration.status = Status.CONFIRMED
        registration.save(update_fields=["status"])
    return queue
