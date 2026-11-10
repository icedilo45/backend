from rest_framework import serializers
from decimal import Decimal, ROUND_HALF_UP
from catalog.models import Product
from accounts.models import Address
from .models import Order, OrderItem, Delivery


class OrderItemWriteSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)


class OrderCreateSerializer(serializers.Serializer):
    """B2C order create — customer is request.user."""
    items = OrderItemWriteSerializer(many=True)
    shipping_address_id = serializers.IntegerField(required=False, allow_null=True)
    delivery_provider = serializers.ChoiceField(
        choices=["external_manual", "self_pickup"],
        default="external_manual",
    )
    customer_notes = serializers.CharField(required=False, allow_blank=True, default="")
    delivery_notes = serializers.CharField(required=False, allow_blank=True, default="")
    delivery_latitude = serializers.FloatField(required=False, allow_null=True)
    delivery_longitude = serializers.FloatField(required=False, allow_null=True)

    def validate_items(self, items):
        if not items:
            raise serializers.ValidationError("Cart is empty.")
        return items

    def _quantize_coord(self, value):
        if value is None:
            return None
        return Decimal(str(value)).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)

    def validate(self, attrs):
        user = self.context["request"].user
        provider = attrs.get("delivery_provider", "external_manual")
        attrs["customer"] = user
        attrs["delivery_latitude"] = self._quantize_coord(attrs.get("delivery_latitude"))
        attrs["delivery_longitude"] = self._quantize_coord(attrs.get("delivery_longitude"))

        if provider == "external_manual":
            addr_id = attrs.get("shipping_address_id")
            if not addr_id:
                raise serializers.ValidationError(
                    {"shipping_address_id": "Required for home delivery."}
                )
            try:
                address = Address.objects.get(pk=addr_id, user=user)
            except Address.DoesNotExist:
                raise serializers.ValidationError(
                    {"shipping_address_id": "Invalid address."}
                )
            attrs["shipping_address"] = address
        else:
            # Pickup: use default address if any, else first, else error with helpful msg
            addr_id = attrs.get("shipping_address_id")
            if addr_id:
                try:
                    attrs["shipping_address"] = Address.objects.get(pk=addr_id, user=user)
                except Address.DoesNotExist:
                    raise serializers.ValidationError(
                        {"shipping_address_id": "Invalid address."}
                    )
            else:
                address = (
                    Address.objects.filter(user=user, is_default=True).first()
                    or Address.objects.filter(user=user).first()
                )
                if not address:
                    raise serializers.ValidationError(
                        {
                            "shipping_address_id": "Add at least one address on your profile (used as contact reference)."
                        }
                    )
                attrs["shipping_address"] = address

        resolved = []
        for line in attrs["items"]:
            try:
                product = Product.objects.get(pk=line["product_id"], is_active=True)
            except Product.DoesNotExist:
                raise serializers.ValidationError(
                    f"Product id {line['product_id']} not found."
                )
            if line["quantity"] < product.min_order_qty:
                raise serializers.ValidationError(
                    f"{product.name}: minimum order is {product.min_order_qty}."
                )
            if line["quantity"] > product.stock_quantity:
                raise serializers.ValidationError(
                    f"{product.name}: only {product.stock_quantity} in stock."
                )
            resolved.append({"product": product, "quantity": line["quantity"]})
        attrs["resolved_items"] = resolved
        return attrs

    def create(self, validated_data):
        customer = validated_data["customer"]
        address = validated_data["shipping_address"]
        items_data = validated_data["resolved_items"]
        provider = validated_data.get("delivery_provider", "external_manual")

        lat = validated_data.get("delivery_latitude")
        lng = validated_data.get("delivery_longitude")
        # Fall back to address coordinates if client did not send a live pin
        if lat is None and getattr(address, "latitude", None) is not None:
            lat = address.latitude
        if lng is None and getattr(address, "longitude", None) is not None:
            lng = address.longitude

        order = Order.objects.create(
            customer=customer,
            shipping_address=address,
            channel="b2c",
            status="pending_payment",
            delivery_provider=provider,
            customer_notes=validated_data.get("customer_notes", ""),
            delivery_notes=validated_data.get("delivery_notes", ""),
            delivery_latitude=lat,
            delivery_longitude=lng,
        )

        subtotal = Decimal("0")
        for line in items_data:
            product = line["product"]
            qty = line["quantity"]
            unit_price = product.price
            item = OrderItem(
                order=order,
                product=product,
                product_name=product.name,
                sku=product.sku,
                unit_price=unit_price,
                quantity=qty,
            )
            item.line_total = unit_price * qty
            item.save()
            subtotal += item.line_total
            product.stock_quantity = max(0, product.stock_quantity - qty)
            product.save(update_fields=["stock_quantity"])

        order.subtotal = subtotal
        order.delivery_fee = Decimal("0")
        order.total = subtotal
        order.save()

        Delivery.objects.create(
            order=order,
            provider="pickup" if provider == "self_pickup" else "bolt_send",
            status="pending",
            notes="Customer will pick up" if provider == "self_pickup" else "Arrange external delivery; customer pays rider.",
        )
        return order


class OrderFulfillmentSerializer(serializers.Serializer):
    delivery_provider = serializers.ChoiceField(
        choices=["external_manual", "self_pickup"]
    )
    delivery_notes = serializers.CharField(required=False, allow_blank=True, default="")


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product",
            "product_name",
            "sku",
            "unit_price",
            "quantity",
            "line_total",
        ]


class DeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = Delivery
        fields = [
            "id",
            "provider",
            "status",
            "tracking_code",
            "tracking_url",
            "driver_name",
            "driver_phone",
            "estimated_delivery",
            "actual_delivery",
            "notes",
        ]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    delivery = DeliverySerializer(read_only=True)
    customer_email = serializers.EmailField(source="customer.email", read_only=True)
    shipping_summary = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "order_number",
            "customer_email",
            "channel",
            "status",
            "subtotal",
            "delivery_fee",
            "total",
            "delivery_provider",
            "customer_notes",
            "delivery_notes",
            "external_tracking_code",
            "external_delivery_url",
            "shipping_summary",
            "items",
            "delivery",
            "paid_at",
            "created_at",
            "updated_at",
        ]

    def get_shipping_summary(self, obj):
        a = obj.shipping_address
        lat = obj.delivery_latitude if obj.delivery_latitude is not None else (a.latitude if a else None)
        lng = obj.delivery_longitude if obj.delivery_longitude is not None else (a.longitude if a else None)
        if not a and lat is None:
            return None
        parts = []
        if a:
            parts = [a.street, a.city, a.region]
            if a.digital_address:
                parts.append(a.digital_address)
        if lat is not None and lng is not None:
            maps = f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"
        elif a:
            maps = f"https://www.google.com/maps/search/?api=1&query={a.street},{a.city},{a.region}"
        else:
            maps = None
        return {
            "id": a.id if a else None,
            "label": a.label if a else "Pin",
            "line": ", ".join(p for p in parts if p) if parts else "GPS pin only",
            "phone_hint": obj.customer.phone if obj.customer_id else "",
            "latitude": str(lat) if lat is not None else None,
            "longitude": str(lng) if lng is not None else None,
            "maps_url": maps,
        }
