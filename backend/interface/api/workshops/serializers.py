from rest_framework import serializers

from domain.workshops.entities import Workshop as WorkshopEntity
from infrastructure.db.models import Registration, Workshop


class WorkshopSerializer(serializers.ModelSerializer):
    seats_taken = serializers.IntegerField(read_only=True)
    seats_left = serializers.SerializerMethodField()

    class Meta:
        model = Workshop
        fields = [
            "id",
            "title",
            "description",
            "starts_at",
            "capacity",
            "seats_taken",
            "seats_left",
        ]

    def get_seats_left(self, obj: Workshop) -> int:
        # The seat rule lives in the domain. The serializer only asks it.
        entity = WorkshopEntity(id=obj.pk, title=obj.title, capacity=obj.capacity)
        return entity.free_seats(obj.seats_taken)


class RegistrationSerializer(serializers.ModelSerializer):
    """Read side: the user's own registrations."""

    workshop_title = serializers.CharField(source="workshop.title", read_only=True)

    class Meta:
        model = Registration
        fields = ["id", "workshop", "workshop_title", "status", "created_at"]
        read_only_fields = fields


class RegistrationResultSerializer(serializers.Serializer):
    """Shapes the DTO a use case returns. Same JSON as RegistrationSerializer."""

    id = serializers.IntegerField()
    workshop = serializers.IntegerField(source="workshop_id")
    workshop_title = serializers.CharField()
    status = serializers.CharField()
    created_at = serializers.DateTimeField()
