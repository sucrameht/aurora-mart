from django import forms
from storefront.models import Product

class ProductCreateForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'sku_code',
            'product_name',
            'product_description',
            'product_category',
            'product_subcategory',
            'quantity_on_hand',
            'reorder_quantity',
            'unit_price',
            'product_rating'
        ]