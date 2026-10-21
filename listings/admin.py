from django.contrib import admin

from moderation.audit import log_action

from .models import Category, Listing, ListingImage


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "slug", "position", "is_active")
    list_filter = ("is_active", "parent")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        log_action(request, "category.change" if change else "category.create", obj)


class ImageInline(admin.TabularInline):
    model = ListingImage
    extra = 0


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ("title", "seller", "category", "price", "quantity", "status", "created_at")
    list_filter = ("status", "condition", "category")
    search_fields = ("title", "brand", "seller__username")
    raw_id_fields = ("seller",)
    inlines = [ImageInline]
    actions = ["suspend", "publish"]

    @admin.action(description="Suspendre les annonces sélectionnées")
    def suspend(self, request, queryset):
        for listing in queryset:
            listing.status = Listing.Status.SUSPENDED
            listing.save(update_fields=["status", "updated_at"])
            log_action(request, "listing.suspend", listing)

    @admin.action(description="Republier les annonces sélectionnées")
    def publish(self, request, queryset):
        for listing in queryset:
            listing.status = Listing.Status.PUBLISHED
            listing.save(update_fields=["status", "updated_at"])
            log_action(request, "listing.publish", listing)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        log_action(request, "listing.change" if change else "listing.create", obj, ", ".join(form.changed_data))

    def delete_model(self, request, obj):
        log_action(request, "listing.delete", obj)
        super().delete_model(request, obj)
