from rest_framework import serializers
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from .models import User, PharmacyProfile, Address


def _get_pharmacy(user):
    try:
        return user.pharmacy_profile
    except PharmacyProfile.DoesNotExist:
        return None


def _quantize_coord(value):
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value)).quantize(
            Decimal("0.000001"), rounding=ROUND_HALF_UP
        )
    except (InvalidOperation, ValueError, TypeError):
        raise serializers.ValidationError("Invalid coordinate.")


class UserSerializer(serializers.ModelSerializer):
    has_pharmacy_profile = serializers.SerializerMethodField()
    address_count = serializers.SerializerMethodField()
    can_checkout = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "phone",
            "firebase_uid",
            "account_type",
            "has_pharmacy_profile",
            "address_count",
            "can_checkout",
        ]
        read_only_fields = ["id", "email", "firebase_uid", "account_type"]

    def get_has_pharmacy_profile(self, obj):
        return _get_pharmacy(obj) is not None

    def get_address_count(self, obj):
        return obj.addresses.count()

    def get_can_checkout(self, obj):
        return bool(obj.phone) and obj.addresses.exists()


class AddressSerializer(serializers.ModelSerializer):
    latitude = serializers.FloatField(required=False, allow_null=True)
    longitude = serializers.FloatField(required=False, allow_null=True)

    class Meta:
        model = Address
        fields = [
            "id",
            "label",
            "street",
            "city",
            "region",
            "digital_address",
            "landmark",
            "latitude",
            "longitude",
            "is_default",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate_latitude(self, value):
        return _quantize_coord(value)

    def validate_longitude(self, value):
        return _quantize_coord(value)

    def validate_digital_address(self, value):
        if value is None:
            return ""
        return str(value).strip()[:50]


class PharmacyProfileSerializer(serializers.ModelSerializer):
    """B2B pharmacy business profile."""

    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = PharmacyProfile
        fields = [
            "id",
            "user_email",
            "business_name",
            "registration_number",
            "pharmacy_council_license",
            "fda_related_info",
            "contact_person",
            "contact_phone",
            "tax_id",
            "verification_status",
            "is_profile_complete",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user_email",
            "verification_status",
            "is_profile_complete",
            "created_at",
            "updated_at",
        ]
