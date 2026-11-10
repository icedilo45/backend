from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Firebase-backed user.
    Used for B2C customers now; same user can later get a PharmacyProfile for B2B.
    """
    firebase_uid = models.CharField(max_length=128, unique=True, db_index=True)
    phone = models.CharField(max_length=20, blank=True)

    # account_type helps future B2B routing without a hard split
    ACCOUNT_TYPES = [
        ("customer", "Customer (B2C)"),
        ("pharmacy", "Pharmacy (B2B)"),
        ("both", "Customer + Pharmacy"),
    ]
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES, default="customer")

    def __str__(self):
        return self.email or self.firebase_uid

    @property
    def display_name(self):
        name = f"{self.first_name} {self.last_name}".strip()
        return name or self.email or self.firebase_uid


class Address(models.Model):
    """
    Delivery address for a user (B2C).
    Same model can later be reused by pharmacies if needed.
    """
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="addresses"
    )
    label = models.CharField(max_length=50, default="Home")  # Home, Work, Other
    street = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    region = models.CharField(max_length=100)  # Greater Accra, Ashanti, etc.
    digital_address = models.CharField(
        max_length=50, blank=True, help_text="Ghana Post GPS digital address"
    )
    landmark = models.CharField(max_length=255, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Addresses"
        ordering = ["-is_default", "-created_at"]

    def __str__(self):
        return f"{self.label} – {self.city}, {self.region}"


class PharmacyProfile(models.Model):
    """
    B2B only (later). Not required for B2C checkout.
    Kept so wholesale / pharmacy bulk can be added without redesign.
    """
    VERIFICATION_STATUS = [
        ("pending", "Pending review"),
        ("verified", "Verified"),
        ("rejected", "Rejected"),
        ("suspended", "Suspended"),
    ]

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="pharmacy_profile"
    )
    business_name = models.CharField(max_length=255)
    registration_number = models.CharField(max_length=100)
    pharmacy_council_license = models.CharField(max_length=100, blank=True)
    fda_related_info = models.CharField(max_length=255, blank=True)
    contact_person = models.CharField(max_length=150)
    contact_phone = models.CharField(max_length=20)
    tax_id = models.CharField(max_length=50, blank=True)
    verification_status = models.CharField(
        max_length=20, choices=VERIFICATION_STATUS, default="pending"
    )
    verification_notes = models.TextField(blank=True)
    is_profile_complete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Pharmacy Profile (B2B)"
        verbose_name_plural = "Pharmacy Profiles (B2B)"

    def __str__(self):
        return f"{self.business_name} ({self.verification_status})"
