from collections.abc import Callable

from django.db import transaction

from application.workshops.interfaces import UnitOfWork

from .repositories import DjangoRegistrationRepository, DjangoWorkshopRepository


class DjangoUnitOfWork(UnitOfWork):
    """One database transaction. Create a new instance for every use-case call."""

    def __init__(self) -> None:
        self.workshops = DjangoWorkshopRepository()
        self.registrations = DjangoRegistrationRepository()
        self._atomic = transaction.atomic()

    def __enter__(self):
        self._atomic.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._atomic.__exit__(exc_type, exc, tb)

    def on_commit(self, callback: Callable[[], None]) -> None:
        transaction.on_commit(callback)
