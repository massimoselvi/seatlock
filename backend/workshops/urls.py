from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("workshops", views.WorkshopViewSet, basename="workshop")
router.register(
    "organizer/workshops", views.OrganizerWorkshopViewSet, basename="organizer-workshop"
)
router.register("registrations", views.RegistrationViewSet, basename="registration")

urlpatterns = [
    path("health/", views.health),
    path("auth/signup/", views.SignupView.as_view()),
    path("auth/login/", views.LoginView.as_view()),
    path("auth/logout/", views.LogoutView.as_view()),
    path("auth/me/", views.MeView.as_view()),
    path("", include(router.urls)),
]
