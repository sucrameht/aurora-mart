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
    path('orders/<int:pk>/', CustomerTransactionDetailView.as_view(), name='customer_order_detail'),
    path('orders/<int:pk>/review/', RateOrderView.as_view(), name='rate_order'),
    path('orders/<int:pk>/cancel/', CancelOrderView.as_view(), name='cancel_order'),
    path('orders/<int:pk>/request-refund/', RequestRefundView.as_view(), name='request_refund'),
    path('buy-now/<str:sku_code>/', BuyNowView.as_view(), name='buy_now'),
    path('chat/', ChatListView.as_view(), name='chat_list'),
    path('chat/start/<str:sku_code>/', StartChatView.as_view(), name='start_chat'),
    path('chat/thread/<int:thread_id>/', ChatThreadView.as_view(), name='chat_thread'),
    path('product/<str:sku_code>/', ProductDetailView.as_view(), name='product_detail'),

    path('profile/settings/', ProfileSettingsView.as_view(), name='profile_settings'),
    path('profile/addresses/', ManageAddressesView.as_view(), name='manage_addresses'),
    path('profile/addresses/edit/<int:pk>/', EditShippingAddressView.as_view(), name='edit_shipping_address'),
    path('profile/addresses/delete/<int:pk>/', DeleteShippingAddressView.as_view(), name='delete_shipping_address'),
    path('profile/manage-cards/', ManageCardsView.as_view(), name='manage_cards'),
    path('profile/manage-cards/edit/<int:pk>/', EditCardView.as_view(), name='edit_card'),
    path('profile/manage-cards/delete/<int:pk>/', DeleteCardView.as_view(), name='delete_card'),
    path('profile/change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('profile/my-vouchers/', MyVouchersView.as_view(), name='my_vouchers'),
    path('profile/delete-account/', DeleteAccountView.as_view(), name='delete_account'),
    path('add-card/', AddCardView.as_view(), name='add_card'),
]