from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .accounts import views as accounts
from .health import health
from .organizer.views import OrganizerWorkshopViewSet
from .workshops.views import RegistrationViewSet, WorkshopViewSet

router = DefaultRouter()
router.register("workshops", WorkshopViewSet, basename="workshop")
router.register("organizer/workshops", OrganizerWorkshopViewSet, basename="organizer-workshop")
router.register("registrations", RegistrationViewSet, basename="registration")

urlpatterns = [
    path("health/", health),
    path("auth/signup/", accounts.SignupView.as_view()),
    path("auth/login/", accounts.LoginView.as_view()),
    path("auth/logout/", accounts.LogoutView.as_view()),
    path("auth/me/", accounts.MeView.as_view()),
    path("", include(router.urls)),
]
