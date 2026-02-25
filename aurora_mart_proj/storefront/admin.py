from django.contrib import admin
from .models import Product, Transactions, OrderItem, Voucher

# Register your models here.
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    fields = ['product', 'quantity_purchased', 'get_unit_price', 'subtotal_products_bought']
    readonly_fields = ['product', 'get_unit_price', 'subtotal_products_bought']
    can_delete = False

    def get_unit_price(self, obj):
        return obj.product.unit_price
    get_unit_price.short_description = 'Unit Price'
    
@admin.register(Transactions)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_user_id', 'get_username', 'transaction_datetime', 'num_of_products', 'total_spent')
    inlines = [OrderItemInline]
    list_filter = ['transaction_datetime']
    search_fields = ['user__username', 'user__id']

    def get_user_id(self, obj):
        return obj.user.id
    # allows for sorting
    get_user_id.admin_order_field = 'user__id'
    get_user_id.short_description = 'User ID'
    
    def get_username(self, obj):
        return obj.user.username
    get_username.admin_order_field = 'user__username'
    get_username.short_description = 'Username'

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('sku_code', 'product_name', 'product_category', 'product_subcategory', 'unit_price', 'quantity_on_hand', 'product_rating')
    list_filter = ['product_category', 'product_subcategory']
    search_fields = ['sku_code', 'product_name']

admin.site.register(Voucher)
