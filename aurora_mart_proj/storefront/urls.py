from django.urls import path
from . import views

urlpatterns = [
    path('', views.StorefrontView.as_view(), name='storefront_home'),
    path('cart/', views.CartView.as_view(), name='view_cart'),
]