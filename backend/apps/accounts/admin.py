from django.contrib import admin

from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("nombre", "whatsapp", "email", "is_active", "is_staff", "activated_at")
    search_fields = ("nombre", "whatsapp", "email")
    exclude = ("password",)
    readonly_fields = ("failed_attempts", "locked_until", "activated_at", "last_login")
