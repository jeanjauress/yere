from django.contrib import admin

from moderation.audit import log_action

from .models import Order, OrderItem, Payment


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("listing", "title", "unit_price", "quantity")
    can_delete = False


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ("provider", "amount", "status", "reference", "created_at", "confirmed_at")
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "buyer", "seller", "total_amount", "status", "payment_status", "created_at")
    list_filter = ("status", "payment_status", "delivery_mode", "created_at")
    search_fields = ("order_number", "buyer__username", "seller__username", "recipient_phone")
    readonly_fields = ("order_number", "buyer", "seller", "items_amount", "delivery_fee", "total_amount",
                       "created_at", "updated_at", "delivered_at")
    inlines = [OrderItemInline, PaymentInline]

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        log_action(request, "order.change", obj, ", ".join(form.changed_data))
