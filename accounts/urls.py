from django.urls import path
from .views import MeView, AddressViewSet, PharmacyProfileView

urlpatterns = [
    path("me/", MeView.as_view(), name="accounts-me"),
    path("pharmacy-profile/", PharmacyProfileView.as_view(), name="pharmacy-profile"),
    path(
        "addresses/",
        AddressViewSet.as_view({"get": "list", "post": "create"}),
        name="address-list",
    ),
    path(
        "addresses/<int:pk>/",
        AddressViewSet.as_view(
            {
                "get": "retrieve",
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="address-detail",
    ),
]
