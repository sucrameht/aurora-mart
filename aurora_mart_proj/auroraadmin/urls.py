from django.urls import path
from .views import analytics_view, ProductInventoryView, AddProductView, DeleteProductView
from django.contrib.auth.views import LogoutView

app_name = 'auroraadmin'

urlpatterns = [
    path('analytics/', analytics_view, name='admin_dashboard'),
    path('product/', ProductInventoryView.as_view(), name='product'),
    path('product/add', AddProductView.as_view(), name='product_add'),
    path('product/<str:sku_code>/delete/', DeleteProductView.as_view(), name='product_delete'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
]