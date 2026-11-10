from rest_framework import serializers
from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(source="order.order_number", read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "order",
            "order_number",
            "amount",
            "currency",
            "status",
            "paystack_reference",
            "paystack_access_code",
            "paystack_authorization_url",
            "paid_at",
            "created_at",
        ]
        read_only_fields = fields


class InitializePaymentSerializer(serializers.Serializer):
    order_id = serializers.UUIDField()
    callback_url = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class VerifyPaymentSerializer(serializers.Serializer):
    reference = serializers.CharField()
