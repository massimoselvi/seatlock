from dataclasses import dataclass
from datetime import datetime

from domain.workshops.entities import Registration, RegistrationStatus


@dataclass(frozen=True)
class RegistrationResult:
    """What a use case returns. The interface layer turns this into JSON."""

    id: int
    workshop_id: int
    status: RegistrationStatus
    created_at: datetime | None

    @classmethod
    def from_entity(cls, registration: Registration) -> "RegistrationResult":
        assert registration.id is not None
        return cls(
            id=registration.id,
            workshop_id=registration.workshop_id,
            status=registration.status,
            created_at=registration.created_at,
        )
