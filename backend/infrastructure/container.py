"""Composition root: the one place that picks concrete classes for the ports.

Each call returns a fresh use case with its own unit of work, so nothing is shared between
requests. Views and Celery tasks call these factories and never name a concrete class.
"""

from application.workshops.services import CancelRegistration, PromoteWaitlist, RegisterForWorkshop

from .cache.workshop_list import DjangoWorkshopListCache
from .db.unit_of_work import DjangoUnitOfWork
from .messaging.queue import CeleryWaitlistPromotionQueue
from .notifications.mailer import EmailPromotionNotifier


def register_for_workshop() -> RegisterForWorkshop:
    return RegisterForWorkshop(DjangoUnitOfWork(), DjangoWorkshopListCache())


def cancel_registration() -> CancelRegistration:
    return CancelRegistration(
        DjangoUnitOfWork(), DjangoWorkshopListCache(), CeleryWaitlistPromotionQueue()
    )


def promote_waitlist() -> PromoteWaitlist:
    return PromoteWaitlist(DjangoUnitOfWork(), DjangoWorkshopListCache(), EmailPromotionNotifier())
