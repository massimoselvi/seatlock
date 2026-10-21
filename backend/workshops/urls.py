from django.urls import include, path
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("workshops", views.WorkshopViewSet, basename="workshop")

urlpatterns = [
    path("health/", views.health),
    path("auth/signup/", views.SignupView.as_view()),
    path("auth/login/", obtain_auth_token),
    path("auth/logout/", views.LogoutView.as_view()),
    path("auth/me/", views.MeView.as_view()),
    path("", include(router.urls)),
]
