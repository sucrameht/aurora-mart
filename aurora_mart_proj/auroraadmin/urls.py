from django.urls import path
from .views import analytics_view, ProductInventoryView, AddProductView, DeleteProductView, TransactionListView, TransactionDetailView, VoucherManagementView, CustomerListView, CustomerVoucherAssignView, ProductActionsView, AdminUserView
from django.contrib.auth.views import LogoutView

app_name = 'auroraadmin'

urlpatterns = [
    path('analytics/', analytics_view, name='admin_dashboard'),
    path('product/', ProductInventoryView.as_view(), name='product'),
    path('product/add', AddProductView.as_view(), name='product_add'),
    path('product/<str:sku_code>/actions/', ProductActionsView.as_view(), name='product_actions'),
    path('product/<str:sku_code>/delete/', DeleteProductView.as_view(), name='product_delete'),
    path('transactions/', TransactionListView.as_view(), name='transactions_list'),
    path('transactions/<int:pk>/', TransactionDetailView.as_view(), name='transaction_detail'),
    path('vouchers/', VoucherManagementView.as_view(), name='voucher_list'),
    path('customers/', CustomerListView.as_view(), name='customers_list'),
    path('customer/<int:user_id>/add-vouchers/', CustomerVoucherAssignView.as_view(), name="customer_add_vouchers"),
    path('admin-users/', AdminUserView.as_view(), name='admin_users'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
]