from django.db import models
from django.conf import settings
from catalog.models import Product
from accounts.models import Address, PharmacyProfile
import uuid


class Order(models.Model):
    """
    B2C order: belongs to a customer User.
    pharmacy is optional for future B2B wholesale orders.
    """
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("pending_payment", "Pending Payment"),
        ("paid", "Paid"),
        ("confirmed", "Confirmed"),
        ("preparing", "Preparing"),
        ("ready_for_delivery", "Ready for Delivery"),
        ("out_for_delivery", "Out for Delivery"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
        ("refunded", "Refunded"),
    ]

    DELIVERY_PROVIDER_CHOICES = [
        ("external_manual", "External (Bolt Send / Yango / Courier)"),
        ("partner_api", "Partner API (future)"),
        ("self_pickup", "Self Pickup"),
    ]

    CHANNEL_CHOICES = [
        ("b2c", "Consumer (B2C)"),
        ("b2b", "Pharmacy wholesale (B2B)"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_number = models.CharField(max_length=20, unique=True, editable=False)

    # B2C primary
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders",
    )
    # B2B later (nullable)
    pharmacy = models.ForeignKey(
        PharmacyProfile,
        on_delete=models.PROTECT,
        related_name="orders",
        null=True,
        blank=True,
    )
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES, default="b2c")

    shipping_address = models.ForeignKey(
        Address, on_delete=models.PROTECT, related_name="orders"
    )
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="draft")

    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    delivery_provider = models.CharField(
        max_length=30,
        choices=DELIVERY_PROVIDER_CHOICES,
        default="external_manual",
    )
    delivery_notes = models.TextField(blank=True)
    customer_notes = models.TextField(blank=True)

    external_tracking_code = models.CharField(max_length=100, blank=True)
    external_delivery_url = models.URLField(blank=True)

    paid_at = models.DateTimeField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    # GPS pin captured at order time (for staff maps / Bolt)
    delivery_latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    delivery_longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    TERMINAL_STATUSES = frozenset({"delivered", "cancelled", "refunded"})

    def save(self, *args, **kwargs):
        if not self.order_number:
            last = Order.objects.order_by("-created_at").first()
            seq = 1
            if last and last.order_number:
                try:
                    seq = int(last.order_number.split("-")[-1]) + 1
                except (ValueError, IndexError):
                    pass
            self.order_number = f"PB-{seq:06d}"

        # Lock terminal statuses — cannot be changed once set
        if self.pk:
            try:
                previous = Order.objects.get(pk=self.pk)
                if previous.status in self.TERMINAL_STATUSES and self.status != previous.status:
                    raise ValueError(
                        f"Order status '{previous.status}' is final and cannot be changed."
                    )
            except Order.DoesNotExist:
                pass

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.order_number} – {self.customer}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    product_name = models.CharField(max_length=255)
    sku = models.CharField(max_length=64)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.PositiveIntegerField()
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

    def save(self, *args, **kwargs):
        self.line_total = self.unit_price * self.quantity
        if not self.product_name:
            self.product_name = self.product.name
        if not self.sku:
            self.sku = self.product.sku
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quantity} × {self.product_name}"


class Delivery(models.Model):
    """
    External delivery (Bolt Send / Yango). Customer pays rider separately.
    """
    STATUS_CHOICES = [
        ("pending", "Pending arrangement"),
        ("booked", "Booked with provider"),
        ("picked_up", "Picked up"),
        ("in_transit", "In transit"),
        ("delivered", "Delivered"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    ]

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="delivery")
    provider = models.CharField(max_length=50, default="bolt_send")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    tracking_code = models.CharField(max_length=100, blank=True)
    tracking_url = models.URLField(blank=True)
    driver_name = models.CharField(max_length=100, blank=True)
    driver_phone = models.CharField(max_length=20, blank=True)
    estimated_delivery = models.DateTimeField(null=True, blank=True)
    actual_delivery = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Delivery for {self.order.order_number} ({self.status})"
