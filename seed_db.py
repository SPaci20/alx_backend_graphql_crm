import os
import django
from django.utils import timezone
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alx_backend_graphql_crm.settings')
django.setup()

from crm.models import Customer, Product, Order


def seed_database():
    """Seed the database with sample data"""
    
    print("Starting database seeding...")
    
    # Clear existing data
    Order.objects.all().delete()
    Product.objects.all().delete()
    Customer.objects.all().delete()
    
    print("Cleared existing data.")
    
    # Create sample customers
    customers_data = [
        {"name": "Alice Johnson", "email": "alice@example.com", "phone": "+1234567890"},
        {"name": "Bob Smith", "email": "bob@example.com", "phone": "123-456-7890"},
        {"name": "Carol Davis", "email": "carol@example.com", "phone": ""},
        {"name": "David Wilson", "email": "david@example.com", "phone": "+1987654321"},
        {"name": "Eva Brown", "email": "eva@example.com", "phone": "555-123-4567"},
    ]
    
    customers = []
    for customer_data in customers_data:
        customer = Customer.objects.create(**customer_data)
        customers.append(customer)
        print(f"Created customer: {customer.name}")
    
    # Create sample products
    products_data = [
        {"name": "Laptop", "price": Decimal("999.99"), "stock": 10},
        {"name": "Mouse", "price": Decimal("25.50"), "stock": 50},
        {"name": "Keyboard", "price": Decimal("75.00"), "stock": 30},
        {"name": "Monitor", "price": Decimal("299.99"), "stock": 15},
        {"name": "Headphones", "price": Decimal("149.99"), "stock": 25},
        {"name": "Webcam", "price": Decimal("89.99"), "stock": 20},
        {"name": "Desk Chair", "price": Decimal("199.99"), "stock": 8},
        {"name": "USB Drive", "price": Decimal("19.99"), "stock": 100},
    ]
    
    products = []
    for product_data in products_data:
        product = Product.objects.create(**product_data)
        products.append(product)
        print(f"Created product: {product.name}")
    
    # Create sample orders
    orders_data = [
        {
            "customer": customers[0],  # Alice
            "products": [products[0], products[1]],  # Laptop, Mouse
            "order_date": timezone.now(),
        },
        {
            "customer": customers[1],  # Bob
            "products": [products[2], products[4]],  # Keyboard, Headphones
            "order_date": timezone.now(),
        },
        {
            "customer": customers[2],  # Carol
            "products": [products[3]],  # Monitor
            "order_date": timezone.now(),
        },
        {
            "customer": customers[3],  # David
            "products": [products[0], products[3], products[1]],  # Laptop, Monitor, Mouse
            "order_date": timezone.now(),
        },
        {
            "customer": customers[4],  # Eva
            "products": [products[7], products[5]],  # USB Drive, Webcam
            "order_date": timezone.now(),
        },
    ]
    
    for order_data in orders_data:
        order = Order.objects.create(
            customer=order_data["customer"],
            order_date=order_data["order_date"]
        )
        order.products.set(order_data["products"])
        order.calculate_total_amount()
        order.save()
        print(f"Created order for {order.customer.name} with total: ${order.total_amount}")
    
    print("\nDatabase seeding completed!")
    print(f"Created {Customer.objects.count()} customers")
    print(f"Created {Product.objects.count()} products") 
    print(f"Created {Order.objects.count()} orders")


if __name__ == "__main__":
    seed_database()