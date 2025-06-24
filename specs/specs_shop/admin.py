from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Product, CartItem, Order, Coupon, Payment, Wishlist, Review, Referral, Notification, ReturnRequest, Invoice, Inventory, Checkout
# from django.contrib.admin.sites import AlreadyRegistered

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('id', 'username', 'email', 'phone_number', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_active')
    search_fields = ('email', 'username', 'phone_number')
    ordering = ('id',)

    fieldsets = (
        (None, {'fields': ('username', 'email', 'password')}),
        ('Personal Info', {'fields': ('phone_number',)}),
        ('Permissions', {'fields': ('is_staff', 'is_active', 'is_superuser', 'groups', 'user_permissions')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'phone_number', 'password1', 'password2', 'is_staff', 'is_active')}
        ),
    )

admin.site.register(CustomUser, CustomUserAdmin)



@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'size', 'color', 'stock')
    search_fields = ('name', 'category', 'color')

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'quantity', 'added_at')


class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'total_price', 'shipping_address', 'status', 'created_at']  # 🆕 Added address
    list_filter = ["status", "created_at"]
    search_fields = ("user__username", "id", "shipping_address")  # 🆕 Search by address



@admin.register(Checkout)
class CheckoutAdmin(admin.ModelAdmin):
    list_display = ['user', 'total_price', 'discount_price', 'final_price', 'created_at']
    readonly_fields = ['total_price', 'discount_price', 'final_price']

# Register Models
admin.site.register(Order, OrderAdmin)
# admin.site.register(OrderItem, OrderItemAdmin)


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_percentage', 'is_active', 'min_order_amount')
    search_fields = ('code',)
    list_filter = ('is_active',)



@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("order", "user", "razorpay_order_id", "status", "amount", "created_at")
    search_fields = ("razorpay_order_id", "razorpay_payment_id")
    list_filter = ("status",)


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'created_at']
    search_fields = ['user__username', 'product__name']
    list_filter = ['created_at']



@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['user__username', 'product__name', 'comment']



@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ['referrer', 'referral_code', 'referred_user', 'reward_points', 'created_at']
    search_fields = ['referral_code', 'referrer__username']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'is_read', 'created_at']
    list_filter = ['is_read']
    search_fields = ['user__username', 'title']


@admin.register(ReturnRequest)
class ReturnRequestAdmin(admin.ModelAdmin):
    list_display = ['user', 'order', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['user__username', 'order__id']


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ['product', 'stock', 'low_stock_threshold', 'last_updated']
    list_filter = ['stock']
    search_fields = ['product__name']


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("order", "generated_at", "pdf_file")
    search_fields = ("order__id", "order__user__username")
