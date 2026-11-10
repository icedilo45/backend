from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from .models import Address, PharmacyProfile, User
from .serializers import UserSerializer, AddressSerializer, PharmacyProfileSerializer


class MeView(APIView):
    """GET/PATCH /api/accounts/me/"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        user = request.user
        for field in ("first_name", "last_name", "phone"):
            if field in request.data:
                setattr(user, field, request.data[field])
        user.save()
        return Response(UserSerializer(user).data)


class AddressViewSet(viewsets.ModelViewSet):
    """CRUD delivery addresses for the logged-in customer."""

    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        address = serializer.save(user=self.request.user)
        if address.is_default:
            Address.objects.filter(user=self.request.user).exclude(
                pk=address.pk
            ).update(is_default=False)

    def perform_update(self, serializer):
        address = serializer.save()
        if address.is_default:
            Address.objects.filter(user=address.user).exclude(pk=address.pk).update(
                is_default=False
            )



class PharmacyProfileView(APIView):
    """
    GET/POST/PATCH /api/accounts/pharmacy-profile/
    B2B: create or update pharmacy business profile for the logged-in user.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = request.user.pharmacy_profile
        except PharmacyProfile.DoesNotExist:
            return Response({"detail": "No pharmacy profile."}, status=status.HTTP_404_NOT_FOUND)
        return Response(PharmacyProfileSerializer(profile).data)

    def post(self, request):
        if hasattr(request.user, "pharmacy_profile"):
            return Response(
                {"detail": "Profile already exists. Use PATCH to update."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ser = PharmacyProfileSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        profile = ser.save(user=request.user)
        user = request.user
        if getattr(user, "account_type", "customer") == "customer":
            user.account_type = "both"
            user.save(update_fields=["account_type"])
        profile.is_profile_complete = bool(
            profile.business_name
            and profile.registration_number
            and profile.contact_phone
        )
        profile.save(update_fields=["is_profile_complete"])
        return Response(
            PharmacyProfileSerializer(profile).data, status=status.HTTP_201_CREATED
        )

    def patch(self, request):
        try:
            profile = request.user.pharmacy_profile
        except PharmacyProfile.DoesNotExist:
            return Response({"detail": "No pharmacy profile."}, status=status.HTTP_404_NOT_FOUND)
        ser = PharmacyProfileSerializer(profile, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        profile.refresh_from_db()
        profile.is_profile_complete = bool(
            profile.business_name and profile.registration_number and profile.contact_phone
        )
        profile.save(update_fields=["is_profile_complete"])
        return Response(PharmacyProfileSerializer(profile).data)
