from django.contrib import admin
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "paystack_reference",
        "order",
        "amount",
        "currency",
        "status",
        "created_at",
    )
    list_filter = ("status", "currency")
    search_fields = ("paystack_reference", "order__order_number")
    readonly_fields = ("created_at", "updated_at", "paid_at", "raw_response")
