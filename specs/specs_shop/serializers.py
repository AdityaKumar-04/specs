from rest_framework import serializers, generics, permissions
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from .models import Product, CartItem, Order, Coupon, Payment, Wishlist, Review, Referral, Notification, ReturnRequest, Invoice, Inventory, Checkout

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'phone_number','is_staff']

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'phone_number']

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=6)

    def validate(self, data):
        user = User.objects.filter(email=data['email']).first()
        if user and user.check_password(data['password']):
            refresh = RefreshToken.for_user(user)
            return {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': UserSerializer(user).data
            }
        raise serializers.ValidationError("Invalid Credentials")
    
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'is_staff']
    
# Product Serializer
class ProductSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(required=False)

    class Meta:
        model = Product
        fields = '__all__'
        extra_kwargs = {
            'image': {'required': False, 'allow_null': True}
        }

    def create(self, validated_data):
        # ✅ Product create karo
        product = super().create(validated_data)

        # ✅ Inventory bhi create karo with product.stock
        Inventory.objects.create(product=product, stock=product.stock)

        return product

# CartItem Serializer
class CartItemSerializer(serializers.ModelSerializer):
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), source='product', write_only=True
    )  # Allows passing product ID
    product = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ['id', 'user', 'product', 'product_id', 'quantity', 'added_at']
        read_only_fields = ['id', 'user', 'added_at']

    def get_product(self, obj):
        return {
            "id": obj.product.id,
            "name": obj.product.name,
            "price": obj.product.price,
            "size": obj.product.size,
            "color": obj.product.color,
            "category": obj.product.category,
            "image": obj.product.image.url if obj.product.image else None
        }


class OrderSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)  # Show cart items in order

    class Meta:
        model = Order
        fields = ['id','order_id', 'user', 'items', 'total_price', 'status', 'shipping_address', 'created_at']
        read_only_fields = ['id', 'user', 'items', 'total_price', 'created_at','order_id']


class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = '__all__'


class CheckoutSerializer(serializers.ModelSerializer):
    cart_items = CartItemSerializer(many=True, read_only=True)
    coupon = CouponSerializer(read_only=True)

    class Meta:
        model = Checkout
        fields = ['id', 'user', 'cart_items', 'total_price', 'coupon', 'discount_price', 'final_price', 'created_at']
        read_only_fields = ['id', 'user', 'cart_items', 'total_price', 'discount_price', 'final_price', 'created_at']

class OrderSerializer(serializers.ModelSerializer):
    items = serializers.StringRelatedField(many=True)
    coupon = CouponSerializer(read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'user', 'items', 'total_price', 'coupon','shipping_address', 'discount_price', 'final_price', 'status', 'created_at']
        # read_only_fields = ['id', 'user', 'items', 'total_price', 'discount_price', 'final_price', 'created_at']


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"


class WishlistSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')
    user_name = serializers.ReadOnlyField(source='user.username')

    class Meta:
        model = Wishlist
        fields = ['id', 'user', 'product', 'product_name', 'user_name', 'created_at']


class ReviewSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')  # User ka naam read-only rakha hai

    class Meta:
        model = Review
        fields = ['id', 'user', 'product', 'rating', 'comment', 'created_at']



class ReferralSerializer(serializers.ModelSerializer):
    referrer = serializers.ReadOnlyField(source='referrer.username')
    referred_user = serializers.ReadOnlyField(source='referred_user.username')

    class Meta:
        model = Referral
        fields = ['id', 'referrer', 'referral_code', 'referred_user', 'reward_points', 'created_at']


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'user', 'title', 'message', 'is_read', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']


class ReturnRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReturnRequest
        fields = ['id', 'user', 'order', 'reason', 'status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'status', 'created_at', 'updated_at']


class InventorySerializer(serializers.ModelSerializer):
    is_low_stock = serializers.ReadOnlyField()

    class Meta:
        model = Inventory
        fields = ['product', 'stock', 'low_stock_threshold', 'is_low_stock', 'last_updated']
        read_only_fields = ['is_low_stock', 'last_updated']


class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = ["order", "generated_at", "pdf_file"]