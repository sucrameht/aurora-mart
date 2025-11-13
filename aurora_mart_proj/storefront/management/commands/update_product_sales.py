import csv
from collections import defaultdict # to hold sku_code:quantity pairs
from django.core.management.base import BaseCommand
from storefront.models import Product
from django.conf import settings
from django.db import transaction

class Command(BaseCommand):
    help = "tally quantity sold from dataset and update the database"

    def handle(self, *args, **options):
        csv_file = "C:/Users/admin/OneDrive - National University of Singapore/Y2S1/IS2108/IS2108 - AY2526S1 - Pair Project/Project_code/aurora-mart/aurora_mart_proj/data/order_items_data.csv"

        sales_tally = defaultdict(int)

        try:
            with open(csv_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    sku_code = row['sku_code']
                    quantity_sold = int(row['quantity_purchased'])
                    sales_tally[sku_code] += quantity_sold

            with transaction.atomic():
                for sku_code, total_quantity in sales_tally.items():
                    Product.objects.filter(sku_code=sku_code).update(num_sold=total_quantity)
            
            self.stdout.write(self.style.SUCCESS(f"Updated num_sold for {len(sales_tally)} products atomically."))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error occurred: {e}"))