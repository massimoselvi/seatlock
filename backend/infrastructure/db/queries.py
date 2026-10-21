"""Read side: querysets for the API. Reads need no use case, so views call these directly."""

from django.db.models import Count, Q, QuerySet

from . import models

CONFIRMED = models.Registration.Status.CONFIRMED
WAITLISTED = models.Registration.Status.WAITLISTED


def workshops_with_seats() -> QuerySet:
    return models.Workshop.objects.annotate(
        seats_taken=Count("registrations", filter=Q(registrations__status=CONFIRMED))
    ).order_by("starts_at", "id")


def organizer_workshops() -> QuerySet:
    return models.Workshop.objects.annotate(
        seats_taken=Count("registrations", filter=Q(registrations__status=CONFIRMED)),
        waitlist_size=Count("registrations", filter=Q(registrations__status=WAITLISTED)),
    ).order_by("starts_at", "id")
