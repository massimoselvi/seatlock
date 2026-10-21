from django.db.models import Count, Q
from django.http import JsonResponse
from rest_framework import generics, permissions, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Registration, Workshop
from .serializers import SignupSerializer, UserSerializer, WorkshopSerializer


def health(request):
    return JsonResponse({"status": "ok"})


class WorkshopViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = WorkshopSerializer
    queryset = Workshop.objects.annotate(
        seats_taken=Count(
            "registrations",
            filter=Q(registrations__status=Registration.Status.CONFIRMED),
        )
    )


class SignupView(generics.CreateAPIView):
    serializer_class = SignupSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes: list = []

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {"token": token.key, "user": UserSerializer(user).data},
            status=status.HTTP_201_CREATED,
        )


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
