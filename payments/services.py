import hashlib
import hmac
import uuid
import requests
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
from .models import Payment
from orders.models import Order


class PaystackError(Exception):
    pass


def _headers():
    return {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }


def initialize_payment(order: Order, callback_url: str | None = None) -> Payment:
    """
    Create a Paystack transaction for the order.
    Amount is in pesewas (GHS * 100).
    """
    if not settings.PAYSTACK_SECRET_KEY:
        raise PaystackError("PAYSTACK_SECRET_KEY is not configured.")

    if order.status not in ("pending_payment", "draft"):
        raise PaystackError(f"Order status '{order.status}' cannot be paid.")

    reference = f"PB-{order.order_number}-{uuid.uuid4().hex[:8]}"
    amount_pesewas = int(Decimal(order.total) * 100)

    payload = {
        "email": order.customer.email,
        "amount": amount_pesewas,
        "currency": settings.PAYSTACK_CURRENCY,
        "reference": reference,
        "metadata": {
            "order_id": str(order.id),
            "order_number": order.order_number,
            "customer_email": order.customer.email,
        },
    }
    if callback_url:
        payload["callback_url"] = callback_url

    resp = requests.post(
        "https://api.paystack.co/transaction/initialize",
        json=payload,
        headers=_headers(),
        timeout=30,
    )
    data = resp.json()
    if not data.get("status"):
        raise PaystackError(data.get("message", "Paystack initialize failed"))

    result = data["data"]
    payment = Payment.objects.create(
        order=order,
        amount=order.total,
        currency=settings.PAYSTACK_CURRENCY,
        status="initialized",
        paystack_reference=reference,
        paystack_access_code=result.get("access_code", ""),
        paystack_authorization_url=result.get("authorization_url", ""),
        raw_response=data,
    )
    return payment


def verify_payment(reference: str) -> Payment:
    """Verify a transaction with Paystack and mark order paid if successful."""
    if not settings.PAYSTACK_SECRET_KEY:
        raise PaystackError("PAYSTACK_SECRET_KEY is not configured.")

    try:
        payment = Payment.objects.select_related("order").get(paystack_reference=reference)
    except Payment.DoesNotExist:
        raise PaystackError("Payment reference not found.")

    if payment.status == "success":
        return payment

    resp = requests.get(
        f"https://api.paystack.co/transaction/verify/{reference}",
        headers=_headers(),
        timeout=30,
    )
    data = resp.json()
    payment.raw_response = data

    if not data.get("status"):
        payment.status = "failed"
        payment.save()
        raise PaystackError(data.get("message", "Verification failed"))

    tx = data["data"]
    if tx.get("status") == "success":
        payment.status = "success"
        payment.paystack_transaction_id = str(tx.get("id", ""))
        payment.paid_at = timezone.now()
        payment.save()

        order = payment.order
        if order.status == "pending_payment":
            order.status = "paid"
            order.paid_at = timezone.now()
            order.save(update_fields=["status", "paid_at", "updated_at"])
    else:
        payment.status = "failed"
        payment.save()

    return payment


def verify_webhook_signature(payload_body: bytes, signature: str) -> bool:
    secret = settings.PAYSTACK_SECRET_KEY.encode("utf-8")
    computed = hmac.new(secret, payload_body, hashlib.sha512).hexdigest()
    return hmac.compare_digest(computed, signature or "")


def refund_payment(payment: Payment, reason: str = "Customer cancelled order") -> Payment:
    """
    Full refund via Paystack for a successful payment.
    https://paystack.com/docs/api/refund/
    """
    if not settings.PAYSTACK_SECRET_KEY:
        raise PaystackError("PAYSTACK_SECRET_KEY is not configured.")

    if payment.status not in ("success",):
        raise PaystackError(f"Cannot refund payment in status '{payment.status}'.")

    if payment.status == "refunded":
        return payment

    amount_pesewas = int(Decimal(payment.amount) * 100)
    payload = {
        "transaction": payment.paystack_reference,
        "amount": amount_pesewas,
        "currency": payment.currency or settings.PAYSTACK_CURRENCY,
        "customer_note": reason,
        "merchant_note": f"Refund for order {payment.order.order_number}",
    }

    resp = requests.post(
        "https://api.paystack.co/refund",
        json=payload,
        headers=_headers(),
        timeout=30,
    )
    data = resp.json()
    payment.raw_response = data

    if not data.get("status"):
        payment.save(update_fields=["raw_response"])
        raise PaystackError(data.get("message", "Paystack refund failed"))

    payment.status = "refunded"
    payment.save(update_fields=["status", "raw_response", "updated_at"])
    return payment
