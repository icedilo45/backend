from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


def health(_request):
    """GET /api/health/ — confirms this NutriPulse backend is running."""
    return JsonResponse(
        {
            "status": "ok",
            "app": "NutriPulse",
            "routes": [
                "/api/catalog/categories/",
                "/api/catalog/products/",
                "/api/accounts/me/",
                "/api/accounts/addresses/",
                "/api/orders/",
                "/api/payments/initialize/",
                "/api/docs/",
            ],
        }
    )


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health, name="health"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/catalog/", include("catalog.urls")),
    path("api/accounts/", include("accounts.urls")),
    path("api/orders/", include("orders.urls")),
    path("api/payments/", include("payments.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
