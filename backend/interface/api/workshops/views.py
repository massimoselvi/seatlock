from django.conf import settings
from django.core.cache import cache
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, NotFound
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from domain.workshops.exceptions import RegistrationNotFound, WorkshopClosed, WorkshopNotFound
from infrastructure import container
from infrastructure.cache import workshop_list as workshop_cache
from infrastructure.db import models, queries

from .serializers import RegistrationResultSerializer, RegistrationSerializer, WorkshopSerializer

MAX_CACHED_PAGE = 1000
# Ids in the URL are digits only: /workshops/abc/ is a plain 404 and never reaches int().
ID_REGEX = r"\d+"


class WorkshopStarted(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "This workshop has already started."
    default_code = "workshop_started"


class WorkshopViewSet(viewsets.ReadOnlyModelViewSet):
    throttle_scope = None  # per-action kwargs must exist as class attributes
    lookup_value_regex = ID_REGEX
    serializer_class = WorkshopSerializer
    queryset = queries.workshops_with_seats()

    def list(self, request, *args, **kwargs):
        # Only the page number may vary the cache key. Any other query parameter is ignored,
        # so a client cannot fill Redis with one entry per random string.
        page = request.query_params.get("page", "1")
        if not (page.isdecimal() and 1 <= int(page) <= MAX_CACHED_PAGE):
            return super().list(request, *args, **kwargs)  # let DRF answer, uncached

        key = workshop_cache.list_key(int(page))
        data = cache.get(key)
        if data is None:
            data = super().list(request, *args, **kwargs).data
            cache.set(key, data, settings.WORKSHOP_LIST_CACHE_SECONDS)
        return Response(data)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[permissions.IsAuthenticated],
        throttle_classes=[ScopedRateThrottle],
        throttle_scope="registration",
    )
    def register(self, request, pk=None):
        try:
            result = container.register_for_workshop().execute(
                user_id=request.user.pk, workshop_id=int(pk)
            )
        except WorkshopNotFound:
            raise NotFound("Workshop not found.") from None
        except WorkshopClosed:
            raise WorkshopStarted from None
        return Response(RegistrationResultSerializer(result).data, status=status.HTTP_200_OK)


class RegistrationViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    throttle_scope = None
    lookup_value_regex = ID_REGEX
    serializer_class = RegistrationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return models.Registration.objects.filter(user=self.request.user).select_related("workshop")

    @action(
        detail=True,
        methods=["post"],
        throttle_classes=[ScopedRateThrottle],
        throttle_scope="registration",
    )
    def cancel(self, request, pk=None):
        try:
            result = container.cancel_registration().execute(
                user_id=request.user.pk, registration_id=int(pk)
            )
        except RegistrationNotFound:
            raise NotFound("Registration not found.") from None
        return Response(RegistrationResultSerializer(result).data)
