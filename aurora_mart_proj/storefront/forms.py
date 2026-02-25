# In forms.py
from django import forms
from datetime import date

class CartActionForm(forms.Form):
    action = forms.CharField(max_length=50)
    sku_code = forms.CharField(max_length=20, required=False)
    quantity = forms.IntegerField(required=False, min_value=0)
    voucher_code = forms.CharField(max_length=50, required=False)

class CardForm(forms.Form):
    nickname = forms.CharField(max_length=100, label="Card Nickname", help_text="e.g., Personal, Work")
    cardholder_name = forms.CharField(max_length=255, label="Cardholder Name")
    card_number = forms.CharField(max_length=19, min_length=13, label="Card Number", widget=forms.TextInput(attrs={'placeholder': '•••• •••• •••• ••••'}))
    expiry_month = forms.IntegerField(min_value=1, max_value=12, label="Expiry Month")
    expiry_year = forms.IntegerField(min_value=date.today().year, label="Expiry Year")
    cvv = forms.CharField(max_length=4, min_length=3, label="CVV", widget=forms.PasswordInput)

    def clean_card_number(self):
        card_number = self.cleaned_data['card_number'].replace(' ', '')
        if not card_number.isdigit():
            raise forms.ValidationError("Card number must only contain digits.")
        
        s = 0
        num_digits = len(card_number)
        oddeven = num_digits & 1
        for i in range(num_digits):
            digit = int(card_number[i])
            if not (( i & 1 ) ^ oddeven ):
                digit = digit * 2
            if digit > 9:
                digit = digit - 9
            s = s + digit
        if s % 10 != 0:
            raise forms.ValidationError("Invalid card number.")
        return card_number

    def clean(self):
        cleaned_data = super().clean()
        expiry_month = cleaned_data.get("expiry_month")
        expiry_year = cleaned_data.get("expiry_year")

        if expiry_month and expiry_year:
            today = date.today()
            if expiry_year == today.year and expiry_month < today.month:
                raise forms.ValidationError("The expiry date cannot be in the past.")
        return cleaned_data