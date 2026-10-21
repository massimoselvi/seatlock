"""Seat allocation rules.

Every function that changes seat counts locks the Workshop row with
SELECT ... FOR UPDATE, so concurrent requests for the same workshop are
serialized and capacity can never be oversold.
"""

from django.db import transaction

from . import rules
from .cache import invalidate_workshop_list
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

    status = rules.status_for_new_registration(workshop.capacity, _confirmed_count(workshop))
    registration = Registration.objects.create(workshop=workshop, user=user, status=status)
    invalidate_workshop_list()
    return registration


@transaction.atomic
def cancel(*, user, registration_id: int) -> Registration:
    """Cancel a registration; a freed seat is offered to the waitlist after commit."""
    registration = Registration.objects.get(pk=registration_id, user=user)
    workshop = Workshop.objects.select_for_update().get(pk=registration.workshop_id)
    registration.refresh_from_db()

    outcome = rules.cancel(rules.RegistrationStatus(registration.status))
    if not outcome.changed:
        return registration

    registration.status = outcome.status
    registration.save(update_fields=["status"])
    invalidate_workshop_list()

    if outcome.freed_seat:
        from .tasks import promote_waitlist

        transaction.on_commit(lambda: promote_waitlist.delay(workshop.pk))
    return registration


@transaction.atomic
def promote_waitlisted(*, workshop_id: int) -> list[Registration]:
    """Fill free seats from the waitlist, oldest first. Returns promoted rows."""
    workshop = Workshop.objects.select_for_update().get(pk=workshop_id)
    confirmed = _confirmed_count(workshop)
    free = rules.free_seats(workshop.capacity, confirmed)
    if free == 0:
        return []

    waitlist = list(
        workshop.registrations.filter(status=Status.WAITLISTED).select_related("user")[:free]
    )
    promoted = rules.select_for_promotion(workshop.capacity, confirmed, waitlist)
    for registration in promoted:
        registration.status = rules.promote(rules.RegistrationStatus(registration.status))
        registration.save(update_fields=["status"])
    if promoted:
        invalidate_workshop_list()
    return promoted
