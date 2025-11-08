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
        file_path = r"C:\Users\admin\OneDrive - National University of Singapore\Y2S1\IS2108\IS2108 - AY2526S1 - Pair Project\Project_code\aurora-mart\aurora_mart_proj\data\generated_transactions_large.csv"

        # clear existing listings (if any)
        OrderItem.objects.all().delete()
        Transactions.objects.all().delete()

        try:
            with open(file_path, "r") as f:
                # handles if the first row is a header row
                reader = csv.DictReader(f)

                for each_row in reader:
                    # ensures all transactions and items are created or none are
                    with transaction.atomic():
                        user = User.objects.get(id=each_row['userid'])
                        naive_time = datetime.strptime(each_row['transaction_datetime'], '%d/%m/%Y %H:%M')
                        current_timezone = timezone.get_current_timezone()
                        transaction_datetime = timezone.make_aware(naive_time, current_timezone)
                        new_transaction = Transactions.objects.create(
                            user=user,
                            transaction_datetime=transaction_datetime
                        )

                        # for the items purchased
                        items_dict = ast.literal_eval(each_row['items'])
                        for sku_code, quantity in items_dict.items():
                            product = Product.objects.get(sku_code=sku_code)
                            OrderItem.objects.create(
                                transactions=new_transaction,
                                product=product,
                                quantity_purchased=quantity
                            )

                self.stdout.write(self.style.SUCCESS("Data Successful Imported"))
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error occurred: {e}"))