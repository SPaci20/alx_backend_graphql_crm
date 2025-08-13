from django.db import models
from django.core.validators import EmailValidator, RegexValidator
from django.utils import timezone
from decimal import Decimal


class Customer(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True, validators=[EmailValidator()])
    phone = models.CharField(
        max_length=20, 
        blank=True, 
        null=True,
        validators=[
            RegexValidator(
                regex=r'^\+?[\d\-\(\)\s]+$',
                message="Phone number must be in format: +1234567890 or 123-456-7890"
            )
        ]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.email})"

    class Meta:
        ordering = ['name']


class Product(models.Model):
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - ${self.price}"

    class Meta:
        ordering = ['name']

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.price <= 0:
            raise ValidationError({'price': 'Price must be positive'})


class Order(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='orders')
    products = models.ManyToManyField(Product, related_name='orders')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    order_date = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order {self.id} - {self.customer.name} - ${self.total_amount}"

    class Meta:
        ordering = ['-order_date']

    def calculate_total_amount(self):
        """Calculate total amount based on associated products"""
        total = sum(product.price for product in self.products.all())
        self.total_amount = total
        return total