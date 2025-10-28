# In forms.py
from django import forms

class CartActionForm(forms.Form):
    action = forms.CharField(max_length=50)
    sku_code = forms.CharField(max_length=20, required=False)
    quantity = forms.IntegerField(required=False, min_value=0)
    voucher_code = forms.CharField(max_length=50, required=False)