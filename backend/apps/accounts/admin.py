from django.contrib import admin

from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("nombre", "whatsapp", "is_active", "is_staff")
    search_fields = ("nombre", "whatsapp")
    exclude = ("password",)
