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

class CustomerVoucherAssignForm(forms.Form):
    vouchers_to_add = forms.ModelMultipleChoiceField(
        queryset=None,
        widget = forms.CheckboxSelectMultiple,
        label="Select Vouchers to assign",
        required=False
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            # get all the vouchers the user already has
            current_vouchers = self.user.userprofile.vouchers.values_list('pk', flat=True)
            # add only the vouchers which are active and not in the user account to be displayed
            self.fields['vouchers_to_add'].queryset = Voucher.objects.filter(is_active=True).exclude(pk__in=current_vouchers)

    def save(self):
        vouchers = self.cleaned_data['vouchers_to_add']
        if vouchers:
            for voucher in vouchers:
                self.user.userprofile.vouchers.add(voucher)
            return len(vouchers)
        return 0