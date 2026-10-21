from django.contrib import admin

from .models import AuditLog, Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("id", "reason", "listing", "reported_user", "reporter", "status", "created_at")
    list_filter = ("status", "reason")
    raw_id_fields = ("reporter", "listing", "reported_user", "handled_by")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor", "action", "target_type", "target_repr", "ip_address")
    list_filter = ("action", "target_type")
    search_fields = ("target_repr", "actor__username", "details")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
