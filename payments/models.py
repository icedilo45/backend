from django.db import models
from orders.models import Order
import uuid


class Payment(models.Model):
    STATUS_CHOICES = [
        ("initialized", "Initialized"),
        ("pending", "Pending"),
        ("success", "Success"),
        ("failed", "Failed"),
        ("abandoned", "Abandoned"),
        ("refunded", "Refunded"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="payments")
    amount = models.DecimalField(max_digits=12, decimal_places=2)  # GHS
    currency = models.CharField(max_length=3, default="GHS")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="initialized")

    # Paystack fields
    paystack_reference = models.CharField(max_length=100, unique=True)
    paystack_access_code = models.CharField(max_length=100, blank=True)
    paystack_authorization_url = models.URLField(blank=True)
    paystack_transaction_id = models.CharField(max_length=50, blank=True)

    raw_response = models.JSONField(default=dict, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.paystack_reference} – {self.amount} {self.currency} ({self.status})"
