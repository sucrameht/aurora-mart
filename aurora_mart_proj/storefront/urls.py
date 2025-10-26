from django.urls import path
from . import views

urlpatterns = [
    path('', views.storefront, name='storefront_home'),
]