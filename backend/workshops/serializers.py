from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

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
        return max(obj.capacity - obj.seats_taken, 0)


User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "is_staff"]


class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    class Meta:
        model = User
        fields = ["username", "email", "password"]
        extra_kwargs = {"email": {"required": True, "allow_blank": False}}

    def validate_email(self, value: str) -> str:
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate(self, attrs):
        validate_password(attrs["password"], User(username=attrs["username"], email=attrs["email"]))
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class RegistrationSerializer(serializers.ModelSerializer):
    workshop_title = serializers.CharField(source="workshop.title", read_only=True)

    class Meta:
        model = Registration
        fields = ["id", "workshop", "workshop_title", "status", "created_at"]
        read_only_fields = fields


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


class RegistrationResultSerializer(serializers.Serializer):
    """Shapes the DTO a use case returns. Same JSON as RegistrationSerializer."""

    id = serializers.IntegerField()
    workshop = serializers.IntegerField(source="workshop_id")
    workshop_title = serializers.CharField()
    status = serializers.CharField()
    created_at = serializers.DateTimeField()
