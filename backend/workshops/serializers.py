from rest_framework import serializers

from .models import Registration, Workshop


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
        return max(obj.capacity - obj.seats_taken, 0)


class RegistrationSerializer(serializers.ModelSerializer):
    workshop_title = serializers.CharField(source="workshop.title", read_only=True)

    class Meta:
        model = Registration
        fields = ["id", "workshop", "workshop_title", "status", "created_at"]
        read_only_fields = fields
