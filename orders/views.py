from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from .models import Order, Delivery
from .serializers import (
    OrderSerializer,
    OrderCreateSerializer,
    OrderFulfillmentSerializer,
)
from payments.models import Payment
from payments.services import refund_payment, PaystackError


class OrderViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        return (
            Order.objects.filter(customer=self.request.user)
            .prefetch_related("items", "delivery", "payments")
            .select_related("customer", "shipping_address")
        )

    def get_serializer_class(self):
        if self.action == "create":
            return OrderCreateSerializer
        return OrderSerializer

    def create(self, request, *args, **kwargs):
        ser = OrderCreateSerializer(data=request.data, context={"request": request})
        ser.is_valid(raise_exception=True)
        order = ser.save()
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(OrderSerializer(page, many=True).data)
        return Response(OrderSerializer(qs, many=True).data)

    def retrieve(self, request, *args, **kwargs):
        return Response(OrderSerializer(self.get_object()).data)

    @action(detail=True, methods=["patch"], url_path="fulfillment")
    def fulfillment(self, request, pk=None):
        order = self.get_object()
        if order.status in Order.TERMINAL_STATUSES:
            return Response(
                {"detail": f"Order is {order.status} and cannot be changed."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ser = OrderFulfillmentSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        provider = ser.validated_data["delivery_provider"]
        notes = ser.validated_data.get("delivery_notes", "")

        order.delivery_provider = provider
        if notes:
            order.delivery_notes = notes
        if order.status == "paid":
            order.status = (
                "ready_for_delivery" if provider == "external_manual" else "confirmed"
            )
        order.save()

        delivery, _ = Delivery.objects.get_or_create(order=order)
        if provider == "self_pickup":
            delivery.provider = "pickup"
            delivery.status = "pending"
            delivery.notes = "Customer will pick up at store."
        else:
            delivery.provider = "bolt_send"
            delivery.status = "pending"
            delivery.notes = (
                "Staff: open Maps pin / address. Book Bolt or courier. "
                "Customer pays delivery fee to rider."
            )
        delivery.save()
        return Response(OrderSerializer(order).data)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        """
        Customer cancels order.
        - If paid: Paystack full refund, status → refunded
        - If unpaid: status → cancelled
        - delivered / already cancelled / refunded: rejected
        """
        order = self.get_object()
        if order.status in Order.TERMINAL_STATUSES:
            return Response(
                {"detail": f"Order is already {order.status}."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if order.status in ("out_for_delivery",):
            return Response(
                {"detail": "Order is already out for delivery. Contact support."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reason = (request.data or {}).get("reason") or "Customer cancelled"

        try:
            with transaction.atomic():
                payment = (
                    Payment.objects.filter(order=order, status="success")
                    .order_by("-paid_at")
                    .first()
                )
                if payment:
                    try:
                        refund_payment(payment, reason=reason)
                    except PaystackError as e:
                        return Response(
                            {"detail": f"Refund failed: {e}"},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    order.status = "refunded"
                else:
                    order.status = "cancelled"
                order.delivery_notes = (
                    (order.delivery_notes + "\n" if order.delivery_notes else "")
                    + f"Cancel: {reason}"
                )
                order.save()

                if hasattr(order, "delivery") and order.delivery:
                    order.delivery.status = "cancelled"
                    order.delivery.save(update_fields=["status", "updated_at"])
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(OrderSerializer(order).data)
