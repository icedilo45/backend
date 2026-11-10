from django.db import models
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="categories/", blank=True, null=True)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="children"
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["sort_order", "name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):
    """
    Food supplement product.
    B2C uses `price` (retail, GHS).
    B2B later can use `wholesale_price` + higher min_order_qty.
    """
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="products"
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True, blank=True)
    sku = models.CharField(max_length=64, unique=True)
    description = models.TextField(blank=True)
    short_description = models.CharField(max_length=300, blank=True)

    # B2C retail price (GHS) — primary for the consumer app
    price = models.DecimalField(max_digits=12, decimal_places=2)
    # B2B wholesale (optional / later)
    wholesale_price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    compare_at_price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )

    unit = models.CharField(
        max_length=40, default="unit", help_text="e.g. bottle, pack, box"
    )
    # B2C default 1; raise for wholesale packs later
    min_order_qty = models.PositiveIntegerField(default=1)
    stock_quantity = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    fda_registration_number = models.CharField(max_length=100, blank=True)
    manufacturer = models.CharField(max_length=200, blank=True)
    country_of_origin = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)
            self.slug = f"{base}-{self.sku.lower()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.sku})"

    @property
    def in_stock(self):
        return self.stock_quantity > 0


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to="products/")
    alt_text = models.CharField(max_length=150, blank=True)
    is_primary = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order"]

    def __str__(self):
        return f"Image for {self.product.name}"
