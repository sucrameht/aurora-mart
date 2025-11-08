from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Product(models.Model):
    sku_code = models.CharField(max_length=20, unique=True, primary_key=True)
    product_name = models.CharField(max_length=150)
    product_description = models.TextField()
    product_category = models.CharField(max_length=100)
    product_subcategory = models.CharField(max_length=100)
    quantity_on_hand = models.IntegerField()
    reorder_quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    product_rating = models.FloatField()

    class Meta:
        ordering = ['product_category', 'product_name']

class Transactions(models.Model):
    user = models.ForeignKey(User, on_delete=models.RESTRICT, related_name="transactions")
    transaction_datetime = models.DateTimeField()
    class Meta:
        # in order to sort by latest first
        ordering = ['-transaction_datetime']

    @property
    def total_spent(self): # for admin view list
        # total value of transaction
        return sum(item.subtotal_products_bought for item in self.items.all())
    
    @property
    def num_of_products(self): # for admin view list
        # total number of products in transaction
        return sum(item.quantity_purchased for item in self.items.all())
    
class OrderItem(models.Model):
    transactions = models.ForeignKey(Transactions, on_delete=models.RESTRICT, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.RESTRICT)
    quantity_purchased = models.IntegerField()

    @property
    def subtotal_products_bought(self):
        return self.quantity_purchased * self.product.unit_price