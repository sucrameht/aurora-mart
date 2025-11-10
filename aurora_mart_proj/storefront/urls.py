from django.urls import path
from .views import *

urlpatterns = [
    path('', StorefrontView.as_view(), name='storefront_home'),
    path('cart/', CartView.as_view(), name='view_cart'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('checkout/', CheckoutView.as_view(), name='checkout'),
    path('add-shipping-address/', AddShippingAddressView.as_view(), name='add_shipping_address'),
    path('profile/edit-profile/', EditProfileView.as_view(), name='edit_profile'),
    path('wallet/', WalletView.as_view(), name='wallet'),
]