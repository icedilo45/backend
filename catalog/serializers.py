from rest_framework import serializers
from .models import Category, Product, ProductImage


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "image", "alt_text", "is_primary", "sort_order"]


class CategoryListSerializer(serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "image_url",
            "parent",
            "product_count",
            "sort_order",
        ]

    def get_product_count(self, obj):
        return obj.products.filter(is_active=True).count()

    def get_image_url(self, obj):
        request = self.context.get("request")
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return None


class CategoryDetailSerializer(CategoryListSerializer):
    children = serializers.SerializerMethodField()

    class Meta(CategoryListSerializer.Meta):
        fields = CategoryListSerializer.Meta.fields + ["children"]

    def get_children(self, obj):
        qs = obj.children.filter(is_active=True)
        return CategoryListSerializer(qs, many=True, context=self.context).data


class ProductListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    primary_image = serializers.SerializerMethodField()
    in_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "slug",
            "sku",
            "short_description",
            "price",
            "compare_at_price",
            "unit",
            "min_order_qty",
            "stock_quantity",
            "in_stock",
            "category",
            "category_name",
            "primary_image",
            "manufacturer",
        ]

    def get_primary_image(self, obj):
        request = self.context.get("request")
        img = obj.images.filter(is_primary=True).first() or obj.images.first()
        if img and request:
            return request.build_absolute_uri(img.image.url)
        return None


class ProductDetailSerializer(ProductListSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    category_slug = serializers.CharField(source="category.slug", read_only=True)

    class Meta(ProductListSerializer.Meta):
        fields = ProductListSerializer.Meta.fields + [
            "description",
            "wholesale_price",
            "fda_registration_number",
            "country_of_origin",
            "images",
            "category_slug",
            "created_at",
            "updated_at",
        ]
