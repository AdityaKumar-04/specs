from django.urls import path
from .views import RegisterView, LoginView, UserListView, ProductListCreateView, ProductDetailView,CartItemListCreateView, CartItemDeleteView, OrderCreateView, OrderListView, ApplyCouponView, CouponListCreateView, CreatePaymentView, VerifyPaymentView, WishlistListCreateView, WishlistDeleteView, ReviewListCreateView, ReviewDetailView, ReferralListCreateView, ApplyReferralCodeView, NotificationListView, MarkNotificationAsReadView, ReturnRequestListView, ReturnRequestCreateView, AdminReturnRequestUpdateView, GenerateInvoiceView, DownloadInvoiceView, InventoryListView, InventoryUpdateView, InventoryListCreateView, AdminOrderListUpdateView, CheckoutCreateView
# from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

urlpatterns = [
    path('signup/', RegisterView.as_view(), name='signup'),
    path('login/', LoginView.as_view(), name='login'),
    path('user/', UserListView.as_view(), name='user'),  # ✅ User details endpoint

    # Product Endpoints
    path('products/', ProductListCreateView.as_view(), name='product-list'),
    path('products/<int:pk>/', ProductDetailView.as_view(), name='product-detail'),

    # Cart Endpoints
    path('cart/', CartItemListCreateView.as_view(), name='cart-list-create'),
    path('cart/<int:pk>/', CartItemDeleteView.as_view(), name='cart-delete'),

    # Order Endpoints
   
    path('orders/', OrderListView.as_view(), name='order-list'),
    path('orders/create/', OrderCreateView.as_view(), name='order-create'),  # ✅ POST request
    path('admin/orders/<int:pk>/', AdminOrderListUpdateView.as_view(), name='admin-order-update'),
    

    path('coupons/', CouponListCreateView.as_view(), name='coupon-list-create'),
    path('order/<int:order_id>/apply-coupon/', ApplyCouponView.as_view(), name='apply-coupon'),

    path('checkout/', CheckoutCreateView.as_view(), name='checkout-create'),

    path("order/<int:order_id>/payment/", CreatePaymentView.as_view(), name="create-payment"),
    path("payment/verify/", VerifyPaymentView.as_view(), name="verify-payment"),

    path('wishlist/', WishlistListCreateView.as_view(), name='wishlist-list-create'),
    path('wishlist/<int:pk>/', WishlistDeleteView.as_view(), name='wishlist-delete'),

    path('products/<int:product_id>/reviews/', ReviewListCreateView.as_view(), name='review-list-create'),
    path('reviews/<int:pk>/', ReviewDetailView.as_view(), name='review-detail'),

    path('referrals/', ReferralListCreateView.as_view(), name='referral-list-create'),
    path('apply-referral/<int:id>/', ApplyReferralCodeView.as_view(), name='apply-referral'),

    path('notifications/', NotificationListView.as_view(), name='notification-list'),
    path('notifications/<int:id>/read/', MarkNotificationAsReadView.as_view(), name='mark-notification-read'),


    path('returns/', ReturnRequestListView.as_view(), name='return-list'),
    path('returns/create/', ReturnRequestCreateView.as_view(), name='return-create'),
    path('returns/<int:pk>/update/', AdminReturnRequestUpdateView.as_view(), name='return-update'),

    path('inventory/', InventoryListCreateView.as_view(), name='inventory-list-create'),
    path('inventory/', InventoryListView.as_view(), name='inventory-list'),
    path('inventory/<int:pk>/update/', InventoryUpdateView.as_view(), name='inventory-update'),

    path('order/<int:order_id>/invoice/generate/', GenerateInvoiceView.as_view(), name="generate-invoice"),
    path('order/<int:order_id>/invoice/download/', DownloadInvoiceView.as_view(), name="download-invoice"),
]
