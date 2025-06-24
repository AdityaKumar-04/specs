from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.response import Response
import razorpay
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import RegisterSerializer, LoginSerializer, CouponSerializer, WishlistSerializer, ReviewSerializer, ReferralSerializer, NotificationSerializer, ReturnRequestSerializer, InventorySerializer, UserSerializer, CheckoutSerializer
from django.contrib.auth import get_user_model
from datetime import date, timedelta
from django.conf import settings
from django.core.mail import send_mail, EmailMessage
from django.db import transaction
from rest_framework import generics, permissions
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.http import FileResponse
from .models import Product, CartItem, Order, Coupon, Payment, Wishlist, Review, Referral, Notification, ReturnRequest, Invoice, Inventory, Checkout
from .serializers import ProductSerializer, CartItemSerializer, OrderSerializer
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
# import random
# import string
# from datetime import datetime
import uuid

client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

User = get_user_model()
# Register View
class RegisterView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': serializer.data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Login View
class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class UserListView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]


# ✅ Product Views
class ProductListCreateView(generics.ListCreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAdminUser]
    parser_classes = [JSONParser, MultiPartParser, FormParser]  # Anyone can view products

    def get_permissions(self):
        if self.request.method == 'GET':  # ✅ Read Allowed for All
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]  # ❌ Only Admin Can Add

# Product Detail View
class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]  # Anyone can view product details

# ✅ CartItem Views
class CartItemListCreateView(generics.ListCreateAPIView):
    serializer_class = CartItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = CartItem.objects.all()

    def get_queryset(self):
        return CartItem.objects.filter(user=self.request.user)  # Fetch only logged-in user’s cart

    def create(self, request, *args, **kwargs):
        print("Incoming Data:", request.data)
        user = request.user
        product_id = request.data.get('product_id')
        quantity = int(request.data.get('quantity', 1))

        # Validate product exists
        product = get_object_or_404(Product, id=product_id)

        # Check if cart item exists (same user, same product, same size & color)
        existing_cart_item = CartItem.objects.filter(
            user=user, product=product
        ).first()

        if existing_cart_item:
            existing_cart_item.quantity += quantity
            existing_cart_item.save()
            return Response(CartItemSerializer(existing_cart_item).data, status=status.HTTP_200_OK)
        else:
            # Create a new cart item
            cart_item = CartItem.objects.create(user=user, product=product, quantity=quantity)
            return Response(CartItemSerializer(cart_item).data, status=status.HTTP_201_CREATED)
    
# CartItem Delete View
class CartItemDeleteView(generics.DestroyAPIView):
    queryset = CartItem.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return get_object_or_404(CartItem, id=self.kwargs['pk'], user=self.request.user)


def generate_order_id():
    return f"ORD-{uuid.uuid4().hex[:10].upper()}"


class OrderCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        cart_items = CartItem.objects.filter(user=user)

        if not cart_items.exists():
            return Response({"error": "Cart is empty."}, status=status.HTTP_400_BAD_REQUEST)

        shipping_address = request.data.get("shipping_address")
        if not shipping_address:
            return Response({"error": "Shipping address is required."}, status=status.HTTP_400_BAD_REQUEST)

        total_price = sum(item.product.price * item.quantity for item in cart_items)

        coupon_code = request.data.get('coupon_code', None)
        coupon = None
        discount_price = 0
        final_price = total_price

        if coupon_code:
            try:
                coupon = Coupon.objects.get(code=coupon_code, is_active=True)
                if total_price >= coupon.min_order_amount:
                    discount_price = (total_price * coupon.discount_percentage) / 100
                    final_price = total_price - discount_price
                else:
                    return Response({
                        "error": f"Minimum order amount should be {coupon.min_order_amount} to use this coupon."
                    }, status=status.HTTP_400_BAD_REQUEST)
            except Coupon.DoesNotExist:
                return Response({"error": "Invalid or inactive coupon."}, status=status.HTTP_400_BAD_REQUEST)

        # Inventory check + stock update
        with transaction.atomic():
            for item in cart_items:
                try:
                    inventory = Inventory.objects.get(product=item.product)
                    if inventory.stock < item.quantity:
                        return Response({
                            "error": f"Not enough stock for {item.product.name}. Available: {inventory.stock}"
                        }, status=status.HTTP_400_BAD_REQUEST)

                    inventory.stock -= item.quantity
                    inventory.save()

                except Inventory.DoesNotExist:
                    return Response({
                        "error": f"Inventory record not found for {item.product.name}"
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
                
                
                # ✅ Generate unique order ID
            custom_order_id = generate_order_id()

            # ✅ Create order with shipping_address
            order = Order.objects.create(
                user=user,
                total_price=total_price,
                coupon=coupon,
                discount_price=discount_price, 
                final_price=final_price,
                shipping_address=shipping_address,  # ✅ Save address
                order_id=custom_order_id  # ✅ Generate and save it 
            )
            order.items.set(cart_items)
            cart_items.delete()  # Clear cart after order creation

        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)
    
class CreateRazorpayOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        amount = request.data.get('amount')
        custom_order_id = request.data.get('custom_order_id')

        if not amount:
            return Response({'error': 'Amount is required'}, status=400)

        client = razorpay.Client(auth=('YOUR_KEY_ID', 'YOUR_SECRET_KEY'))

        payment = client.order.create({
            "amount": int(amount * 100),  # Convert to paisa
            "currency": "INR",
            "receipt": custom_order_id,
            "payment_capture": 1
        })

        return Response({
            "razorpay_order_id": payment['id'],
            "amount": amount * 100
        })


class CheckoutCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        cart_items = CartItem.objects.filter(user=user)

        if not cart_items.exists():
            return Response({"error": "Cart is empty."}, status=status.HTTP_400_BAD_REQUEST)

        total_price = sum(item.product.price * item.quantity for item in cart_items)
        coupon_code = request.data.get('coupon_code', None)

        coupon = None
        discount_price = 0
        final_price = total_price

        if coupon_code:
            try:
                coupon = Coupon.objects.get(code=coupon_code, is_active=True)
                if total_price >= coupon.min_order_amount:
                    discount_price = (total_price * coupon.discount_percentage) / 100
                    final_price = total_price - discount_price
                else:
                    return Response({"error": f"Minimum order amount is {coupon.min_order_amount}."}, status=status.HTTP_400_BAD_REQUEST)
            except Coupon.DoesNotExist:
                return Response({"error": "Invalid or inactive coupon."}, status=status.HTTP_400_BAD_REQUEST)

        # Save checkout data
        checkout = Checkout.objects.create(
            user=user,
            total_price=total_price,
            coupon=coupon,
            discount_price=discount_price,
            final_price=final_price
        )
        checkout.cart_items.set(cart_items)

        return Response(CheckoutSerializer(checkout).data, status=status.HTTP_201_CREATED)


    
# Order List View
class OrderListView(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)
    
class AdminOrderListUpdateView(generics.RetrieveUpdateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        return Order.objects.select_related('user').all()
    


class CouponCreateView(generics.CreateAPIView):
    queryset = Coupon.objects.all()
    serializer_class = CouponSerializer
    permission_classes = [IsAdminUser]  # ✅ Only admins can create a coupon

class CouponDeleteView(generics.DestroyAPIView):
    queryset = Coupon.objects.all()
    serializer_class = CouponSerializer
    permission_classes = [IsAdminUser]  # ✅ Only admins can delete a coupon
    


class ApplyCouponView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        # Get the order for the authenticated user
        order = get_object_or_404(Order, id=order_id, user=request.user)

        # Get coupon code from request body
        coupon_code = request.data.get('coupon_code')
        if not coupon_code:
            return Response({"error": "Coupon code is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Check if the coupon exists and is active
        coupon = Coupon.objects.filter(code=coupon_code, is_active=True).first()
        if not coupon:
            return Response({"error": "Invalid or inactive coupon."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate minimum order amount
        if order.total_price < coupon.min_order_amount:
            return Response({
                "error": f"Minimum order amount should be {coupon.min_order_amount} to use this coupon."
            }, status=status.HTTP_400_BAD_REQUEST)

        # Calculate discount
        discount = (order.total_price * coupon.discount_percentage) / 100
        final_price = order.total_price - discount

        # Update order details
        order.coupon = coupon
        order.discount_price = discount
        order.final_price = final_price
        order.save()

        return Response({
            "message": "Coupon applied successfully!",
            "order_details": OrderSerializer(order).data
        }, status=status.HTTP_200_OK)
    

class CouponListCreateView(generics.ListCreateAPIView):
    queryset = Coupon.objects.all()
    serializer_class = CouponSerializer

    def get_permissions(self):
        if self.request.method == 'POST':  # Only admin can create coupons
            return [IsAdminUser()]
        return super().get_permissions()
    


class CreatePaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        order = get_object_or_404(Order, id=order_id, user=request.user)

        if order.final_price <= 0:
            return Response({"error": "Invalid order amount."}, status=status.HTTP_400_BAD_REQUEST)

        # Create a Razorpay order
        razorpay_order = client.order.create({
            "amount": int(order.final_price * 100),  # Convert amount to paise
            "currency": "INR",
            "payment_capture": 1  # Auto capture
        })

        # Save payment details in the database
        payment = Payment.objects.create(
            order=order,
            user=request.user,
            razorpay_order_id=razorpay_order["id"],
            amount=order.final_price
        )

        return Response({"order_id": razorpay_order["id"], "amount": order.final_price}, status=status.HTTP_201_CREATED)


class VerifyPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        razorpay_order_id = request.data.get("razorpay_order_id")
        razorpay_payment_id = request.data.get("razorpay_payment_id")
        razorpay_signature = request.data.get("razorpay_signature")

        payment = get_object_or_404(Payment, razorpay_order_id=razorpay_order_id, user=request.user)

        params_dict = {
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature
        }

        try:
            client.utility.verify_payment_signature(params_dict)
            payment.razorpay_payment_id = razorpay_payment_id
            payment.razorpay_signature = razorpay_signature
            payment.status = "SUCCESS"
            payment.save()

            # ✅ Send email to user
            send_mail(
                subject="Payment Successful - Order Confirmation",
                message=f"Hi {request.user.username},\n\nYour payment of ₹{payment.amount} was successful.\nOrder ID: {payment.order.id}\n\nThank you for shopping with us!",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[request.user.email],
                fail_silently=False
            )

            return Response({"message": "Payment successful!"}, status=status.HTTP_200_OK)

        except razorpay.errors.SignatureVerificationError:
            payment.status = "FAILED"
            payment.save()
            return Response({"error": "Payment verification failed!"}, status=status.HTTP_400_BAD_REQUEST)




class WishlistListCreateView(generics.ListCreateAPIView):
    queryset = Wishlist.objects.all()
    serializer_class = WishlistSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user) 


class WishlistDeleteView(generics.DestroyAPIView):
    serializer_class = WishlistSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Wishlist.objects.filter(user=self.request.user)


class ReviewListCreateView(generics.ListCreateAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        product_id = self.kwargs['product_id']
        return Review.objects.filter(product_id=product_id)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class ReviewDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]



class ReferralListCreateView(generics.ListCreateAPIView):
    serializer_class = ReferralSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Referral.objects.filter(referrer=self.request.user)

    def perform_create(self, serializer):
        serializer.save(referrer=self.request.user)

class ApplyReferralCodeView(generics.UpdateAPIView):
    queryset = User.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'

    def update(self, request, *args, **kwargs):
        user = self.get_object()
        referral_code = request.data.get('referral_code')

        try:
            referral = Referral.objects.get(referral_code=referral_code, referred_user=None)
            referral.referred_user = user
            referral.reward_points += 100  # Reward points
            referral.save()
            return Response({"message": "Referral code applied successfully!", "reward_points": referral.reward_points}, status=200)
        except Referral.DoesNotExist:
            return Response({"error": "Invalid or already used referral code"}, status=400)
        


class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')

class MarkNotificationAsReadView(generics.UpdateAPIView):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'

    def update(self, request, *args, **kwargs):
        notification = self.get_object()
        if notification.user != request.user:
            return Response({"error": "You can't mark this notification as read!"}, status=403)
        
        notification.is_read = True
        notification.save()
        return Response({"message": "Notification marked as read!"}, status=200)



class ReturnRequestCreateView(generics.CreateAPIView):
    serializer_class = ReturnRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        order_id = self.request.data.get("order")
        try:
            order = Order.objects.get(id=order_id, user=self.request.user)
            if order.status != "delivered":
                return Response({"error": "Only delivered orders can be returned."}, status=400)
            serializer.save(user=self.request.user, order=order)
        except Order.DoesNotExist:
            return Response({"error": "Order not found or you do not have permission."}, status=400)

class ReturnRequestListView(generics.ListAPIView):
    serializer_class = ReturnRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ReturnRequest.objects.filter(user=self.request.user).order_by('-created_at')

class AdminReturnRequestUpdateView(generics.UpdateAPIView):
    queryset = ReturnRequest.objects.all()
    serializer_class = ReturnRequestSerializer
    permission_classes = [permissions.IsAdminUser]

    def update(self, request, *args, **kwargs):
        return_request = self.get_object()
        new_status = request.data.get("status")

        if new_status not in ["approved", "rejected", "refunded"]:
            return Response({"error": "Invalid status."}, status=400)

        return_request.status = new_status
        return_request.save()

        if new_status == "refunded":
            # Implement Razorpay Refund Logic Here (Optional)
            pass

        return Response({"message": f"Return request updated to {new_status}."}, status=200)

class InventoryListCreateView(generics.ListCreateAPIView):
    queryset = Inventory.objects.all()
    serializer_class = InventorySerializer
    permission_classes = [permissions.IsAdminUser] # Only admin can create inventory records

class InventoryListView(generics.ListAPIView):
    queryset = Inventory.objects.all()
    serializer_class = InventorySerializer
    permission_classes = [permissions.IsAdminUser]

class InventoryUpdateView(generics.UpdateAPIView):
    queryset = Inventory.objects.all()
    serializer_class = InventorySerializer
    permission_classes = [permissions.IsAdminUser]


class GenerateInvoiceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id, user=request.user)
            invoice, created = Invoice.objects.get_or_create(order=order)

            if created:
                invoice.generate_invoice()

            return Response({"message": "Invoice generated successfully!", "invoice_url": invoice.pdf_file.url})
        except Order.DoesNotExist:
            return Response({"error": "Order not found."}, status=404)

class DownloadInvoiceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id, user=request.user)
            invoice = Invoice.objects.get(order=order)
            pdf_path = invoice.pdf_file.path

            return FileResponse(open(pdf_path, 'rb'), as_attachment=True, filename=f"invoice_{order.id}.pdf")
        except (Order.DoesNotExist, Invoice.DoesNotExist):
            return Response({"error": "Invoice not found."}, status=404)

class SendInvoiceEmailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id, user=request.user)
            invoice = Invoice.objects.get(order=order)

            email = EmailMessage(
                subject=f"Invoice for Order #{order.id}",
                body="Please find the attached invoice for your order.",
                to=[request.user.email]
            )
            email.attach_file(invoice.pdf_file.path)
            email.send()

            return Response({"message": "Invoice sent successfully!"})
        except (Order.DoesNotExist, Invoice.DoesNotExist):
            return Response({"error": "Invoice not found."}, status=404)






















































































































