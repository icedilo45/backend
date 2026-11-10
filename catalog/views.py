from rest_framework import viewsets, filters
from rest_framework.permissions import AllowAny
from .models import Category, Product
from .serializers import (
    CategoryListSerializer,
    CategoryDetailSerializer,
    ProductListSerializer,
    ProductDetailSerializer,
)


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Public catalog categories.
    GET /api/catalog/categories/          – top-level categories
    GET /api/catalog/categories/?all=1    – all categories
    GET /api/catalog/categories/{slug}/   – detail + children
    """
    permission_classes = [AllowAny]
    authentication_classes = []  # public: skip Firebase
    lookup_field = "slug"
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description"]
    ordering_fields = ["sort_order", "name"]

    def get_queryset(self):
        qs = Category.objects.filter(is_active=True)
        if self.action == "list" and self.request.query_params.get("all") != "1":
            qs = qs.filter(parent__isnull=True)
        return qs.select_related("parent").prefetch_related("children", "products")

    def get_serializer_class(self):
        if self.action == "retrieve":
            return CategoryDetailSerializer
        return CategoryListSerializer


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Public product catalog.
    GET /api/catalog/products/
    GET /api/catalog/products/?category=vitamins
    GET /api/catalog/products/?in_stock=1
    GET /api/catalog/products/?search=omega
    GET /api/catalog/products/{slug}/
    """
    permission_classes = [AllowAny]
    authentication_classes = []  # public: skip Firebase
    lookup_field = "slug"
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "sku", "short_description", "description", "manufacturer"]
    ordering_fields = ["price", "name", "created_at", "stock_quantity"]
    ordering = ["name"]

    def get_queryset(self):
        qs = (
            Product.objects.filter(is_active=True)
            .select_related("category")
            .prefetch_related("images")
        )

        category_slug = self.request.query_params.get("category")
        if category_slug:
            qs = qs.filter(category__slug=category_slug)

        in_stock = self.request.query_params.get("in_stock")
        if in_stock in ("1", "true", "True"):
            qs = qs.filter(stock_quantity__gt=0)

        return qs

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ProductDetailSerializer
        return ProductListSerializer
