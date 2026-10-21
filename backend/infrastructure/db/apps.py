from django.apps import AppConfig


class DbConfig(AppConfig):
    """The Django app that owns the tables.

    The label stays `workshops`, so table names (`workshops_workshop`) and the migration history
    do not change when the code moves.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "infrastructure.db"
    label = "workshops"
