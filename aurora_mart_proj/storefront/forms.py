# In forms.py
from django import forms

class CartActionForm(forms.Form):
    action = forms.CharField(max_length=10)
    sku_code = forms.CharField(max_length=20)
    quantity = forms.IntegerField(required=False, min_value=0)