class DomainError(Exception):
    """Base class for every business-rule failure. Carries no HTTP or database meaning."""


class WorkshopNotFound(DomainError):
    pass


class RegistrationNotFound(DomainError):
    pass


class WorkshopClosed(DomainError):
    """The workshop has started, so nobody can join it any more."""


class InvalidStatusTransition(DomainError):
    pass
