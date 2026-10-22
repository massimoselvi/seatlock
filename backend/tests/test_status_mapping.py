"""The domain and the ORM each list the registration statuses. These tests keep the lists equal.

The repository converts with `RegistrationStatus(row.status)`, so a status added only to the model
would raise ValueError at runtime. These tests fail first. They need no database.
"""

from domain.workshops.entities import ACTIVE_STATUSES, RegistrationStatus
from infrastructure.db.models import Registration


def test_domain_and_orm_have_the_same_statuses():
    assert {s.value for s in RegistrationStatus} == {s.value for s in Registration.Status}


def test_domain_and_orm_agree_on_which_statuses_are_active():
    assert {s.value for s in ACTIVE_STATUSES} == {s.value for s in Registration.ACTIVE_STATUSES}


def test_every_orm_status_converts_to_a_domain_status():
    for status in Registration.Status:
        assert RegistrationStatus(status.value).value == status.value
