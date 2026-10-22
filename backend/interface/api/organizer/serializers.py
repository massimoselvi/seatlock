from rest_framework import serializers

from infrastructure.db.models import Registration
from interface.api.workshops.serializers import WorkshopSerializer


class OrganizerWorkshopSerializer(WorkshopSerializer):
    waitlist_size = serializers.IntegerField(read_only=True)

    class Meta(WorkshopSerializer.Meta):
        fields = [*WorkshopSerializer.Meta.fields, "waitlist_size"]


class OrganizerRegistrationSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = Registration
        fields = ["id", "username", "email", "status", "created_at"]
        read_only_fields = fields
