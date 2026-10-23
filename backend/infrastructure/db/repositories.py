"""Django ORM implementations of the repository ports. Rows in, domain entities out."""

from collections.abc import Sequence

from application.workshops.interfaces import RegistrationRepository, WorkshopRepository
from domain.workshops.entities import ACTIVE_STATUSES, Registration, RegistrationStatus, Workshop
from domain.workshops.exceptions import RegistrationNotFound, WorkshopNotFound

from . import models


def _registration(row: models.Registration) -> Registration:
    return Registration(
        id=row.pk,
        workshop_id=row.workshop_id,
        user_id=row.user_id,
        status=RegistrationStatus(row.status),
        user_email=row.user.email,
        created_at=row.created_at,
    )


class DjangoWorkshopRepository(WorkshopRepository):
    def lock(self, workshop_id: int) -> Workshop:
        # SELECT ... FOR UPDATE: concurrent requests for this workshop queue up on the row.
        try:
            row = models.Workshop.objects.select_for_update().get(pk=workshop_id)
        except models.Workshop.DoesNotExist:
            raise WorkshopNotFound(workshop_id) from None
        return Workshop(id=row.pk, title=row.title, capacity=row.capacity, starts_at=row.starts_at)


class DjangoRegistrationRepository(RegistrationRepository):
    def _rows(self):
        return models.Registration.objects.select_related("user")

    def find_active(self, workshop_id: int, user_id: int) -> Registration | None:
        row = (
            self._rows()
            .filter(workshop_id=workshop_id, user_id=user_id, status__in=ACTIVE_STATUSES)
            .first()
        )
        return _registration(row) if row else None

    def count_confirmed(self, workshop_id: int) -> int:
        return models.Registration.objects.filter(
            workshop_id=workshop_id, status=RegistrationStatus.CONFIRMED
        ).count()

    def count_waitlisted(self, workshop_id: int) -> int:
        return models.Registration.objects.filter(
            workshop_id=workshop_id, status=RegistrationStatus.WAITLISTED
        ).count()

    def waitlist(self, workshop_id: int, limit: int) -> Sequence[Registration]:
        if limit <= 0:
            return []
        rows = self._rows().filter(workshop_id=workshop_id, status=RegistrationStatus.WAITLISTED)
        return [_registration(row) for row in rows[:limit]]

    def get_for_user(self, registration_id: int, user_id: int) -> Registration:
        try:
            return _registration(self._rows().get(pk=registration_id, user_id=user_id))
        except models.Registration.DoesNotExist:
            raise RegistrationNotFound(registration_id) from None

    def add(self, registration: Registration) -> Registration:
        row = models.Registration.objects.create(
            workshop_id=registration.workshop_id,
            user_id=registration.user_id,
            status=registration.status,
        )
        return _registration(self._rows().get(pk=row.pk))

    def save(self, registration: Registration) -> None:
        models.Registration.objects.filter(pk=registration.id).update(status=registration.status)
