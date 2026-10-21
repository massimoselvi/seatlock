from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("workshops", views.WorkshopViewSet, basename="workshop")
router.register("registrations", views.RegistrationViewSet, basename="registration")

urlpatterns = [
    path("health/", views.health),
    path("", include(router.urls)),
]
