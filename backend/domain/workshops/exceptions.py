class DomainError(Exception):
    """Base class for every business-rule failure. Carries no HTTP or database meaning."""


class WorkshopNotFound(DomainError):
    pass


class RegistrationNotFound(DomainError):
    pass


class InvalidStatusTransition(DomainError):
    pass
