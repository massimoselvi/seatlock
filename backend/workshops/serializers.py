from rest_framework import serializers

from .models import Workshop


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
