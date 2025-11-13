import csv
# for safely converting dictionary data passed in from the csv file
import ast 
from datetime import datetime
from django.core.management.base import BaseCommand
from storefront.models import Transactions, OrderItem, Product
from django.contrib.auth.models import User
# to store the data before transferring to the required endpoint one shot
from django.db import transaction
from django.utils import timezone

class Command(BaseCommand):
    help = "Loads the transactions from the dataset"

    def handle(self, *args, **options):
        transaction_file = r"C:\Users\admin\OneDrive - National University of Singapore\Y2S1\IS2108\IS2108 - AY2526S1 - Pair Project\Project_code\aurora-mart\aurora_mart_proj\data\transactions_data.csv"
        order_items_file = r"C:\Users\admin\OneDrive - National University of Singapore\Y2S1\IS2108\IS2108 - AY2526S1 - Pair Project\Project_code\aurora-mart\aurora_mart_proj\data\order_items_data.csv"

        try:
            # ensures all transactions and items are created or none are
            with transaction.atomic():
                with open(transaction_file, "r") as f:
                    # handles if the first row is a header row
                    reader = csv.DictReader(f)
                    for each_row in reader:
                        each_row = {k: v.strip() for k, v in each_row.items()}

                        user = User.objects.get(id=each_row['user_id'])
                        print("user id linked")
                        naive_time = datetime.strptime(each_row['transaction_datetime'], '%d/%m/%Y %H:%M')
                        print('transaction date time stripped')
                        current_timezone = timezone.get_current_timezone()
                        transaction_datetime = timezone.make_aware(naive_time, current_timezone)
                        print('transaction datetime aware')
                        
                        Transactions.objects.create(
                            id=int(each_row['transaction_id']),
                            user=user,
                            transaction_datetime=transaction_datetime,
                            shipping_first_name=each_row['shipping_first_name'],
                            shipping_last_name=each_row['shipping_last_name'],
                            shipping_phone=each_row['shipping_phone'],
                            shipping_address=each_row['shipping_address'],
                            shipping_city=each_row['shipping_city'],
                            shipping_state=each_row['shipping_state'],
                            shipping_postal_code=each_row['shipping_postal_code'],
                            status='Delivery Completed',
                            voucher_value=each_row['voucher'],
                            payment_method='Card',
                        )
                print("loading transaction done, moving to load order items")

                with open(order_items_file, 'r') as f:
                    reader = csv.DictReader(f)
                    print("Processing order item")
                    for each_row in reader:
                        transaction_obj = Transactions.objects.get(id=int(each_row['transaction_id']))
                        print('transaction obtained')
                        product = Product.objects.get(sku_code=each_row['sku_code'])
                        print('product obtained')
                        OrderItem.objects.create(
                            transactions=transaction_obj,
                            product=product,
                            quantity_purchased=int(each_row['quantity_purchased']),
                            price_at_purchase=float(each_row['price_at_purchase']),
                            rating=0,
                            text_review=''
                        )
                        print("order item created")

                self.stdout.write(self.style.SUCCESS("Data Successful Imported"))
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error occurred: {e}"))