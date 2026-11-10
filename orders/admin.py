from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import Order, OrderItem, Delivery


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product_name", "sku", "unit_price", "quantity", "line_total")
    can_delete = False


class DeliveryInline(admin.StackedInline):
    model = Delivery
    extra = 0
    fields = (
        "provider",
        "status",
        "tracking_code",
        "tracking_url",
        "driver_name",
        "driver_phone",
        "notes",
        "estimated_delivery",
        "actual_delivery",
    )


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_number",
        "customer_contact",
        "status",
        "delivery_provider",
        "total_display",
        "maps_button",
        "created_at",
    )
    list_filter = ("status", "delivery_provider", "channel", "created_at")
    search_fields = (
        "order_number",
        "customer__email",
        "customer__phone",
        "customer__first_name",
        "customer__last_name",
    )
    list_select_related = ("customer", "shipping_address")
    inlines = [OrderItemInline, DeliveryInline]
    actions = (
        "mark_confirmed",
        "mark_preparing",
        "mark_ready_for_delivery",
        "mark_out_for_delivery",
        "mark_delivered",
    )
    readonly_fields = (
        "order_number",
        "created_at",
        "updated_at",
        "paid_at",
        "maps_button",
        "delivery_latitude",
        "delivery_longitude",
        "customer_contact",
        "address_block",
    )
    fieldsets = (
        (
            "Order",
            {
                "fields": (
                    "order_number",
                    "status",
                    "channel",
                    "delivery_provider",
                    "total",
                    "subtotal",
                    "delivery_fee",
                    "paid_at",
                    "created_at",
                    "updated_at",
                )
            },
        ),
        (
            "Customer & delivery pin (tap Maps to open)",
            {
                "fields": (
                    "customer",
                    "customer_contact",
                    "shipping_address",
                    "address_block",
                    "delivery_latitude",
                    "delivery_longitude",
                    "maps_button",
                    "customer_notes",
                    "delivery_notes",
                )
            },
        ),
        (
            "External tracking",
            {
                "fields": ("external_tracking_code", "external_delivery_url"),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(description="Customer")
    def customer_contact(self, obj):
        u = obj.customer
        name = f"{u.first_name} {u.last_name}".strip() or u.email
        phone = u.phone or "—"
        return f"{name} · {phone}"

    @admin.display(description="Total")
    def total_display(self, obj):
        return f"GHS {obj.total}"

    @admin.display(description="Address")
    def address_block(self, obj):
        a = obj.shipping_address
        if not a:
            return "—"
        lines = [a.label, a.street, f"{a.city}, {a.region}"]
        if a.digital_address:
            lines.append(a.digital_address)
        if a.landmark:
            lines.append(f"Landmark: {a.landmark}")
        return mark_safe("<br>".join(lines))

    @admin.display(description="Maps / delivery")
    def maps_button(self, obj):
        lat = obj.delivery_latitude
        lng = obj.delivery_longitude
        a = obj.shipping_address
        if lat is not None and lng is not None:
            gmaps = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lng}"
            geo = f"geo:{lat},{lng}?q={lat},{lng}(Delivery)"
            label = f"GPS {lat}, {lng}"
        elif a:
            q = f"{a.street}, {a.city}, {a.region}".replace(" ", "+")
            gmaps = f"https://www.google.com/maps/dir/?api=1&destination={q}"
            geo = f"geo:0,0?q={q}"
            label = f"{a.street}, {a.city}"
        else:
            return "—"
        return format_html(
            '<a class="button" href="{}" target="_blank" rel="noopener" '
            'style="padding:6px 10px;background:#0D9488;color:#fff;'
            'border-radius:6px;text-decoration:none;margin-right:6px;">'
            "Open in Google Maps</a>"
            '<a class="button" href="{}" style="padding:6px 10px;'
            'background:#334155;color:#fff;border-radius:6px;'
            'text-decoration:none;">Maps app</a><br>'
            '<small style="color:#64748b;">{}</small>',
            gmaps,
            geo,
            label,
        )

    def _set_status(self, request, queryset, status):
        updated = 0
        skipped = 0
        for order in queryset:
            if order.status in Order.TERMINAL_STATUSES:
                skipped += 1
                continue
            try:
                order.status = status
                if status == "delivered":
                    from django.utils import timezone

                    order.delivered_at = timezone.now()
                order.save()
                updated += 1
            except ValueError:
                skipped += 1
        self.message_user(
            request,
            f"{updated} updated to {status}; {skipped} skipped (final or locked).",
            messages.SUCCESS if updated else messages.WARNING,
        )

    @admin.action(description="Mark confirmed")
    def mark_confirmed(self, request, queryset):
        self._set_status(request, queryset, "confirmed")

    @admin.action(description="Mark preparing")
    def mark_preparing(self, request, queryset):
        self._set_status(request, queryset, "preparing")

    @admin.action(description="Mark ready for delivery")
    def mark_ready_for_delivery(self, request, queryset):
        self._set_status(request, queryset, "ready_for_delivery")

    @admin.action(description="Mark out for delivery")
    def mark_out_for_delivery(self, request, queryset):
        self._set_status(request, queryset, "out_for_delivery")

    @admin.action(description="Mark delivered (locks order)")
    def mark_delivered(self, request, queryset):
        self._set_status(request, queryset, "delivered")

    def save_model(self, request, obj, form, change):
        try:
            super().save_model(request, obj, form, change)
        except ValueError as e:
            raise ValidationError(str(e))


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = ("order", "provider", "status", "tracking_code", "updated_at")
    list_filter = ("status", "provider")
    search_fields = ("order__order_number", "tracking_code", "driver_phone")
