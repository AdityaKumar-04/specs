from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings  # ✅ Use this to reference the custom user model
import uuid  # Import uuid for generating unique referral codes
from django.template.loader import render_to_string  # Import render_to_string for rendering templates
from weasyprint import HTML  # Import HTML from weasyprint for generating PDFs

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)  # Unique email for login
    phone_number = models.CharField(max_length=15, unique=True, null=False, blank=True)

    USERNAME_FIELD = 'email'  # Login using email instead of username
    REQUIRED_FIELDS = ['username']  # username is still required

    def __str__(self):
        return self.email

# Product Model
class Product(models.Model):
    CATEGORY_CHOICES = [
        ('men', 'Men'),
        ('women', 'Women'),
        ('kids', 'Kids'),
        ('unisex', 'Unisex'),
    ]

    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    size = models.CharField(max_length=50, blank=True, null=True)  # Example: Small, Medium, Large
    color = models.CharField(max_length=50, blank=True, null=True)
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES, default='unisex')
    image = models.ImageField(upload_to='product_images/',blank=True, null=True)  # Image Upload
    description = models.TextField(blank=True, null=True)  # Optional description
    stock = models.PositiveIntegerField(default=0)  # Available stock count

    def __str__(self):
        return f"{self.name} - {self.category}"

# CartItem Model
class CartItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.product.name} ({self.quantity})"
    

class Checkout(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    cart_items = models.ManyToManyField(CartItem)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    coupon = models.ForeignKey('Coupon', on_delete=models.SET_NULL, null=True, blank=True)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    final_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Checkout by {self.user.username} at {self.created_at}"


class Coupon(models.Model):
    code = models.CharField(max_length=20, unique=True)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2)  # Example: 10 for 10% off
    is_active = models.BooleanField(default=True)
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=3000)  # Minimum amount required

    def __str__(self):
        return f"{self.code} - {self.discount_percentage}%"
    

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    items = models.ManyToManyField('CartItem')  
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)  # Coupon applied
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Discounted amount
    final_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Final price after discount
    shipping_address = models.TextField()  # Ensure this field is present
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    order_id = models.CharField(max_length=100, unique=True, blank=True, null=True)
    

    def __str__(self):
        return f"Order {self.id} - {self.user.username} ({self.status})"
    
class Payment(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="payment")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    razorpay_order_id = models.CharField(max_length=255, unique=True)
    razorpay_payment_id = models.CharField(max_length=255, null=True, blank=True)
    razorpay_signature = models.CharField(max_length=255, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=[("PENDING", "Pending"), ("SUCCESS", "Success"), ("FAILED", "Failed")], default="PENDING")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment for Order {self.order.id} - {self.status}"
    
class Wishlist(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')  # Ek user ek hi product ek bar add kar sakta hai.

    def __str__(self):
        return f"{self.user.username} - {self.product.name}"
    

class Review(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveIntegerField(default=1)  # 1-5 rating scale
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')  # Ek user ek product ko ek hi baar review kar sake
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.product.name} ({self.rating})"


class Referral(models.Model):
    referrer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="referrals")
    referral_code = models.CharField(max_length=10, unique=True, default=uuid.uuid4().hex[:10].upper())
    referred_user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="referred_by", null=True, blank=True)
    reward_points = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.referrer.username} referred {self.referred_user.username if self.referred_user else 'N/A'}"

class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.title} ({'Read' if self.is_read else 'Unread'})"


class ReturnRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('refunded', 'Refunded'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="return_requests")
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="returns")
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Return Request for Order {self.order.id} - {self.status}"
    
class Inventory(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name="inventory")
    stock = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=5)
    last_updated = models.DateTimeField(auto_now=True)

    def is_low_stock(self):
        return self.stock <= self.low_stock_threshold

    def __str__(self):
        return f"{self.product.name} - Stock: {self.stock}"
    

class Invoice(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="invoice")
    generated_at = models.DateTimeField(auto_now_add=True)
    pdf_file = models.FileField(upload_to="invoices/", blank=True, null=True)

    def generate_invoice(self):
        """Generate PDF invoice using WeasyPrint"""
        invoice_html = render_to_string("invoice_template.html", {"order": self.order})
        pdf_path = f"media/invoices/invoice_{self.order.id}.pdf"
        
        HTML(string=invoice_html).write_pdf(pdf_path)

        self.pdf_file = pdf_path
        self.save()
