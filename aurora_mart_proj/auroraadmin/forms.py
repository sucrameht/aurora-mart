from django import forms
from storefront.models import Product, Voucher

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
        ]

class VoucherForm(forms.ModelForm):
    expiry_date = forms.DateField(
        widget = forms.DateInput(attrs={'type':'date'}),
        required = False,
        help_text = "Leave blank if no expiry date"
    )

    class Meta:
        model = Voucher
        fields = [
            'code',
            'discount_type',
            'discount_value',
            'expiry_date',
        ]