from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, PharmacyProfile, Address


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "email",
        "firebase_uid",
        "first_name",
        "phone",
        "account_type",
        "is_staff",
        "date_joined",
    )
    list_filter = ("account_type", "is_staff", "is_active")
    search_fields = ("email", "firebase_uid", "first_name", "last_name", "phone")
    ordering = ("-date_joined",)
    readonly_fields = ("date_joined", "last_login")

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal", {"fields": ("first_name", "last_name", "email", "phone")}),
        ("Firebase / Ghana", {"fields": ("firebase_uid", "account_type")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "firebase_uid",
                    "email",
                    "phone",
                    "account_type",
                    "password1",
                    "password2",
                    "is_staff",
                ),
            },
        ),
    )


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("label", "user", "city", "region", "is_default")
    list_filter = ("region", "is_default")
    search_fields = ("street", "city", "digital_address", "user__email")


@admin.register(PharmacyProfile)
class PharmacyProfileAdmin(admin.ModelAdmin):
    list_display = (
        "business_name",
        "contact_person",
        "verification_status",
        "is_profile_complete",
    )
    list_filter = ("verification_status",)
    search_fields = ("business_name", "registration_number")
