from django.contrib import admin

from moderation.audit import log_action

from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("order", "author", "seller", "rating", "is_hidden", "created_at")
    list_filter = ("rating", "is_hidden")
    raw_id_fields = ("order", "author", "seller")

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        log_action(request, "review.change", obj, ", ".join(form.changed_data))
