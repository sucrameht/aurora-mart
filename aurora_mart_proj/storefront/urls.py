from django.urls import path
from .views import StorefrontView, CartView, ProfileView

urlpatterns = [
    path('', StorefrontView.as_view(), name='storefront_home'),
    path('cart/', CartView.as_view(), name='view_cart'),
    path('profile/', ProfileView.as_view(), name='profile'),
]