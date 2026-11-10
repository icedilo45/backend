"""Seed sample categories and products (B2C retail prices in GHS)."""
from django.core.management.base import BaseCommand
from catalog.models import Category, Product
from decimal import Decimal


class Command(BaseCommand):
    help = "Seed sample food-supplement categories and products (GHS retail)"

    def handle(self, *args, **options):
        self.stdout.write("Seeding catalog (B2C)...")

        data = [
            {
                "name": "Vitamins & Minerals",
                "products": [
                    ("Vitamin C 1000mg Tablets", "VIT-C-1000", "55.00", "75.00", "box of 30", 120, "High-potency vitamin C for immune support", "Nature's Way GH"),
                    ("Multivitamin Adult Complete", "MULTI-ADULT", "85.00", "110.00", "bottle of 60", 90, "Daily multivitamin with minerals", "PharmaCare Ghana"),
                    ("Vitamin D3 2000 IU", "VIT-D3-2000", "65.00", None, "bottle of 90 softgels", 80, "Supports bone health and immunity", "NutriLife"),
                ],
            },
            {
                "name": "Omega & Fish Oils",
                "products": [
                    ("Omega-3 Fish Oil 1000mg", "OMG3-1000", "120.00", "150.00", "bottle of 60", 70, "EPA & DHA for heart and brain health", "OceanPure"),
                    ("Cod Liver Oil Capsules", "CLO-CAP", "52.00", None, "bottle of 100", 60, "Traditional cod liver oil with vitamins A & D", "Nordic Health"),
                ],
            },
            {
                "name": "Herbal & Traditional",
                "products": [
                    ("Moringa Leaf Capsules", "MOR-LEAF", "40.00", "55.00", "bottle of 60", 200, "Pure Moringa oleifera leaf powder capsules", "Green Ghana Naturals"),
                    ("Bitter Leaf Extract", "BIT-LEAF", "32.00", None, "bottle of 30", 150, "Traditional bitter leaf herbal extract", "Heritage Herbs"),
                ],
            },
            {
                "name": "Immunity Boosters",
                "products": [
                    ("Zinc + Vitamin C Complex", "ZNC-VITC", "58.00", "72.00", "box of 30", 100, "Zinc gluconate with vitamin C", "ImmunoPlus"),
                    ("Elderberry Syrup Adult", "ELD-SYR", "70.00", None, "bottle 250ml", 50, "Elderberry extract syrup for immune support", "BerryWell"),
                ],
            },
            {
                "name": "Digestive Health",
                "products": [
                    ("Probiotic 10 Billion CFU", "PROB-10B", "95.00", "120.00", "bottle of 30", 80, "Multi-strain probiotic for gut health", "GutCare Labs"),
                    ("Digestive Enzyme Complex", "DIG-ENZ", "78.00", None, "bottle of 60", 65, "Broad-spectrum digestive enzymes", "EnzyHealth"),
                ],
            },
        ]

        created_cats = created_prods = 0
        for idx, cat_data in enumerate(data):
            cat, created = Category.objects.get_or_create(
                name=cat_data["name"],
                defaults={
                    "description": f"{cat_data['name']} food supplements",
                    "sort_order": idx,
                    "is_active": True,
                },
            )
            if created:
                created_cats += 1

            for name, sku, price, wholesale, unit, stock, short, mfr in cat_data["products"]:
                _, p_created = Product.objects.get_or_create(
                    sku=sku,
                    defaults={
                        "category": cat,
                        "name": name,
                        "price": Decimal(price),
                        "wholesale_price": Decimal(wholesale) if wholesale else None,
                        "unit": unit,
                        "min_order_qty": 1,
                        "stock_quantity": stock,
                        "short_description": short,
                        "description": short + ". Available without prescription in Ghana.",
                        "manufacturer": mfr,
                        "country_of_origin": "Ghana / Imported",
                        "is_active": True,
                    },
                )
                if p_created:
                    created_prods += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Categories created: {created_cats}, Products created: {created_prods}"
            )
        )
