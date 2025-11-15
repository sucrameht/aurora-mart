from django.urls import path
from .views import *
from django.contrib.auth.views import LogoutView

app_name = 'auroraadmin'

urlpatterns = [
    path('analytics/', analytics_view, name='admin_dashboard'),
    path('product/', ProductInventoryView.as_view(), name='product'),
    path('product/add', AddProductView.as_view(), name='product_add'),
    path('product/<str:sku_code>/actions/', ProductActionsView.as_view(), name='product_actions'),
    path('product/<str:sku_code>/delete/', DeleteProductView.as_view(), name='product_delete'),
    path('transactions/', TransactionListView.as_view(), name='transactions_list'),
    path('transactions/cancelled/', CancelledTransactionsView.as_view(), name='cancelled_transactions'),
    path('transactions/refunds/', RefundRequestsView.as_view(), name='refund_requests'),
    path('transactions/<int:pk>/', TransactionDetailView.as_view(), name='transaction_detail'),
    path('vouchers/', VoucherManagementView.as_view(), name='voucher_list'),
    path('customers/', CustomerListView.as_view(), name='customers_list'),
    path('customer/<int:user_id>/add-vouchers/', CustomerVoucherAssignView.as_view(), name="customer_add_vouchers"),
    path('admin-users/', AdminUserView.as_view(), name='admin_users'),
    path('dashboard/', DashboardView.as_view(), name='admin_dashboard'),
    path('charts/gender/<str:time_frame>/', GenderChartView.as_view(), name='gender_chart'),
    path('charts/sales-trend/<str:time_frame>/', SalesTrendChartView.as_view(), name='sales_trend_chart'),
    path('charts/revenue_category/<str:time_frame>/', RevenueByCategoryChartView.as_view(), name='revenue_category_chart'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('chat/', AdminChatListView.as_view(), name='admin_chat_list'),
    path('chat/thread/<int:thread_id>/', AdminChatThreadView.as_view(), name='admin_chat_thread'),
]