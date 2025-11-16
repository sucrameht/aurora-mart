from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

# Create your models here.
class Product(models.Model):
    sku_code = models.CharField(max_length=20, unique=True, primary_key=True)
    product_name = models.CharField(max_length=150)
    product_description = models.TextField()
    product_category = models.CharField(max_length=100)
    product_subcategory = models.CharField(max_length=100)
    quantity_on_hand = models.IntegerField()
    reorder_quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)  # Selling price
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # Cost to purchase
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)  # Total inventory cost
    product_rating = models.FloatField()
    num_sold = models.IntegerField(default=0)

    class Meta:
        ordering = ['product_category', 'product_name']

class Transactions(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="transactions")
    transaction_datetime = models.DateTimeField()

    shipping_first_name = models.CharField(max_length=100, blank=True)
    shipping_last_name = models.CharField(max_length=100, blank=True)
    shipping_phone = models.IntegerField(blank=False, null=False)
    shipping_address = models.CharField(max_length=255, blank=True)
    shipping_city = models.CharField(max_length=100, blank=True)
    shipping_state = models.CharField(max_length=100, blank=True)
    shipping_postal_code = models.CharField(max_length=20, blank=True)
    status = models.CharField(
        max_length=50,
        choices=[
            ('Payment Made', 'Payment Made'),
            ('Delivered to Warehouse', 'Delivered to Warehouse'),
            ('Delivery Completed', 'Delivery Completed'),
            ('Cancelled', 'Cancelled'),
            ('Request for Refund', 'Request for Refund'),
            ('Refund Approved', 'Refund Approved'),
            ('Refund Rejected', 'Refund Rejected'),
        ],
        default='Payment Made',
    )
    voucher_value = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    payment_method = models.CharField(
        max_length=20,
        choices=[
            ('Wallet', 'Wallet'),
            ('Card', 'Card')
        ],
        default='Card',
    )
    notes = models.CharField(max_length=500, blank=True, null=True)

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
    # to allow for transactions to be deleted
    transactions = models.ForeignKey(Transactions, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.RESTRICT)
    quantity_purchased = models.IntegerField()
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2)
    rating = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(5)], blank=True, null=True)
    text_review = models.CharField(max_length=256, blank=True, null=True)

    @property
    def subtotal_products_bought(self):
        return self.quantity_purchased * self.price_at_purchase

class CartItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="cart_items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    is_selected = models.BooleanField(default=True)

    class Meta:
        unique_together = ('user', 'product')
    
    @property
    def total_price(self):
        return self.quantity * self.product.unit_price

class Voucher(models.Model):
    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(
        max_length=10,
        choices=[('percent', 'Percentage'), ('amount', 'Fixed Amount')]
    )
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    expiry_date = models.DateField(null=True, blank=True)
    issued_count = models.IntegerField(default=0)
    used_count = models.IntegerField(default=0)
    

    def __str__(self): # for the displaying of voucher code name in customer add voucher
        return self.code
    
class ShippingAddress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    nickname = models.CharField(max_length=100)
    
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone = models.IntegerField(blank=False, null=False)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)

    class Meta:
        # Prevent a user from having two addresses with the same nickname
        unique_together = ('user', 'nickname')

class Card(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="cards")
    nickname = models.CharField(max_length=100)
    cardholder_name = models.CharField(max_length=255)
    last_four = models.CharField(max_length=4)
    expiry_month = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(12)])
    expiry_year = models.IntegerField()

    class Meta:
        unique_together = ('user', 'nickname')

class ChatThread(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='chat_threads')
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_threads')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('product', 'customer')
        ordering = ['-updated_at']

class ChatMessage(models.Model):
    thread = models.ForeignKey(ChatThread, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']