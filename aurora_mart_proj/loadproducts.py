import csv
from storefront.models import Product

def run():
    with open('data/b2c_products_500.csv', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            Product.objects.create(
                sku_code=row['SKU code'],
                product_name=row['Product name'],
                product_description=row['Product description'],
                product_category=row['Product Category'],
                product_subcategory=row['Product Subcategory'],
                quantity_on_hand=int(row['Quantity on hand']),
                reorder_quantity=int(row['Reorder Quantity']),
                unit_price=float(row['Unit price']),
                product_rating=float(row['Product rating'])
            )
    print("Products loaded successfully!")
