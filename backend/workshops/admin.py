from django.contrib import admin

from .models import Registration, Workshop


@admin.register(Workshop)
class WorkshopAdmin(admin.ModelAdmin):
    list_display = ("title", "starts_at", "capacity")


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ("workshop", "user", "status", "created_at")
    list_filter = ("status",)
