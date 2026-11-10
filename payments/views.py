import json
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from orders.models import Order
from .models import Payment
from .serializers import (
    PaymentSerializer,
    InitializePaymentSerializer,
    VerifyPaymentSerializer,
)
from .services import initialize_payment, verify_payment, verify_webhook_signature, PaystackError


class InitializePaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = InitializePaymentSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        order_id = ser.validated_data["order_id"]
        callback_url = ser.validated_data.get("callback_url")

        try:
            order = Order.objects.get(pk=order_id, customer=request.user)
        except Order.DoesNotExist:
            return Response({"detail": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            payment = initialize_payment(order, callback_url=callback_url)
        except PaystackError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)


class VerifyPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = VerifyPaymentSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        reference = ser.validated_data["reference"]

        try:
            payment = verify_payment(reference)
        except PaystackError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Ensure the payment belongs to this customer
        if payment.order.customer_id != request.user.id:
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)

        return Response(PaymentSerializer(payment).data)


class PaystackWebhookView(APIView):
    """POST /api/payments/webhook/paystack/ – no auth, signature verified"""
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        signature = request.META.get("HTTP_X_PAYSTACK_SIGNATURE", "")
        body = request.body

        if not verify_webhook_signature(body, signature):
            return Response({"detail": "Invalid signature"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            event = json.loads(body)
        except json.JSONDecodeError:
            return Response({"detail": "Invalid JSON"}, status=status.HTTP_400_BAD_REQUEST)

        event_type = event.get("event")
        data = event.get("data") or {}

        if event_type == "charge.success":
            reference = data.get("reference")
            if reference:
                try:
                    verify_payment(reference)
                except PaystackError:
                    pass

        return Response({"status": "ok"})


from django.http import HttpResponse
from urllib.parse import urlencode


class PaystackReturnRedirectView(APIView):
    """
    GET /api/payments/callback/
    Paystack only accepts http(s) callback URLs in the dashboard.
    This page receives the browser after payment and deep-links into the app:

        pharmabulk://payment-callback?reference=...&trxref=...

    Use your public HTTPS origin, e.g.:
      https://xxx.ngrok-free.dev/api/payments/callback/
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        params = request.GET.dict()
        qs = urlencode(params) if params else ""
        deep_link = "pharmabulk://payment-callback"
        if qs:
            deep_link = f"{deep_link}?{qs}"

        # Meta refresh + link for cases where custom scheme is blocked briefly
        html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <meta http-equiv="refresh" content="0;url={deep_link}"/>
  <title>Returning to PharmaBulk…</title>
  <style>
    body {{ font-family: system-ui, sans-serif; text-align: center; padding: 48px 16px; }}
    a {{ color: #0D9488; font-weight: 600; }}
  </style>
</head>
<body>
  <p>Payment received. Returning to <strong>PharmaBulk</strong>…</p>
  <p><a href="{deep_link}">Tap here if the app does not open</a></p>
  <script>window.location.replace({deep_link!r});</script>
</body>
</html>"""
        return HttpResponse(html, content_type="text/html")
