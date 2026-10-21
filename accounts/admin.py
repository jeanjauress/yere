from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from moderation.audit import log_action

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "role", "is_active", "is_suspended", "email_verified", "date_joined")
    list_filter = ("role", "is_active", "is_suspended", "email_verified")
    search_fields = ("username", "email", "phone")
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Marketplace", {"fields": ("phone", "city", "bio", "profile_image", "role", "email_verified", "is_suspended")}),
    )
    actions = ["suspend", "reactivate"]

    @admin.action(description="Suspendre les comptes sélectionnés")
    def suspend(self, request, queryset):
        for u in queryset:
            u.is_suspended = True
            u.save(update_fields=["is_suspended"])
            log_action(request, "user.suspend", u)

    @admin.action(description="Réactiver les comptes sélectionnés")
    def reactivate(self, request, queryset):
        for u in queryset:
            u.is_suspended = False
            u.is_active = True
            u.save(update_fields=["is_suspended", "is_active"])
            log_action(request, "user.reactivate", u)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        log_action(request, "user.change" if change else "user.create", obj, ", ".join(form.changed_data))
