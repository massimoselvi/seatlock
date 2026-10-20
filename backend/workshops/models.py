from django.conf import settings
from django.db import models
from django.db.models import Q


class Workshop(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    starts_at = models.DateTimeField()
    capacity = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["starts_at"]
        constraints = [
            models.CheckConstraint(condition=Q(capacity__gt=0), name="workshop_capacity_positive"),
        ]

    def __str__(self) -> str:
        return self.title


class Registration(models.Model):
    class Status(models.TextChoices):
        CONFIRMED = "confirmed"
        WAITLISTED = "waitlisted"
        CANCELLED = "cancelled"

    ACTIVE_STATUSES = (Status.CONFIRMED, Status.WAITLISTED)

    workshop = models.ForeignKey(Workshop, on_delete=models.CASCADE, related_name="registrations")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="registrations"
    )
    status = models.CharField(max_length=12, choices=Status, default=Status.CONFIRMED)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["workshop", "user"],
                condition=Q(status__in=["confirmed", "waitlisted"]),
                name="one_active_registration_per_user",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user} -> {self.workshop} ({self.status})"
