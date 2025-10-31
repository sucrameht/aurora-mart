from django.db import models

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

