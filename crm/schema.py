# crm/schema.py
import graphene
from graphene import relay, ObjectType, Field, String, Int, Float, Date, Boolean
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError
from django.utils import timezone
from decimal import Decimal
import re

from .models import Customer, Product, Order
from .filters import CustomerFilter, ProductFilter, OrderFilter


# Object Types (Updated from your existing schema)
class CustomerType(DjangoObjectType):
    class Meta:
        model = Customer
        fields = '__all__'
        interfaces = (relay.Node,)


class ProductType(DjangoObjectType):
    class Meta:
        model = Product
        fields = '__all__'
        interfaces = (relay.Node,)


class OrderType(DjangoObjectType):
    class Meta:
        model = Order
        fields = '__all__'
        interfaces = (relay.Node,)


# Input Types (from your existing schema)
class CustomerInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    email = graphene.String(required=True)
    phone = graphene.String()


class ProductInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    price = graphene.Decimal(required=True)
    stock = graphene.Int()


class OrderInput(graphene.InputObjectType):
    customer_id = graphene.ID(required=True)
    product_ids = graphene.List(graphene.ID, required=True)
    order_date = graphene.DateTime()


# Error Types (from your existing schema)
class ErrorType(graphene.ObjectType):
    field = graphene.String()
    message = graphene.String()


class CustomerValidationError(graphene.ObjectType):
    index = graphene.Int()
    errors = graphene.List(ErrorType)


# Mutation Output Types (from your existing schema)
class CreateCustomerOutput(graphene.ObjectType):
    customer = graphene.Field(CustomerType)
    message = graphene.String()
    errors = graphene.List(ErrorType)


class BulkCreateCustomersOutput(graphene.ObjectType):
    customers = graphene.List(CustomerType)
    errors = graphene.List(CustomerValidationError)


class CreateProductOutput(graphene.ObjectType):
    product = graphene.Field(ProductType)
    message = graphene.String()
    errors = graphene.List(ErrorType)


class CreateOrderOutput(graphene.ObjectType):
    order = graphene.Field(OrderType)
    message = graphene.String()
    errors = graphene.List(ErrorType)


# Utility Functions (from your existing schema)
def validate_phone(phone):
    """Validate phone number format"""
    if not phone:
        return True
    pattern = r'^\+?[\d\-\(\)\s]+


# Mutations (from your existing schema)
class CreateCustomer(graphene.Mutation):
    class Arguments:
        input = CustomerInput(required=True)

    customer = graphene.Field(CustomerType)
    message = graphene.String()
    errors = graphene.List(ErrorType)

    def mutate(self, info, input):
        errors = []

        # Validate email uniqueness
        if not validate_email_unique(input.email):
            errors.append(ErrorType(field="email", message="Email already exists"))

        # Validate phone format
        if input.phone and not validate_phone(input.phone):
            errors.append(ErrorType(
                field="phone", 
                message="Phone number must be in format: +1234567890 or 123-456-7890"
            ))

        if errors:
            return CreateCustomer(errors=errors, message="Validation failed")

        try:
            customer = Customer.objects.create(
                name=input.name,
                email=input.email,
                phone=input.phone or ""
            )
            return CreateCustomer(
                customer=customer,
                message=f"Customer '{customer.name}' created successfully"
            )
        except Exception as e:
            return CreateCustomer(
                errors=[ErrorType(field="general", message=str(e))],
                message="Failed to create customer"
            )


class BulkCreateCustomers(graphene.Mutation):
    class Arguments:
        input = graphene.List(CustomerInput, required=True)

    customers = graphene.List(CustomerType)
    errors = graphene.List(CustomerValidationError)

    def mutate(self, info, input):
        customers = []
        errors = []

        with transaction.atomic():
            for index, customer_data in enumerate(input):
                customer_errors = []

                # Validate email uniqueness
                if not validate_email_unique(customer_data.email):
                    customer_errors.append(ErrorType(
                        field="email", 
                        message="Email already exists"
                    ))

                # Validate phone format
                if customer_data.phone and not validate_phone(customer_data.phone):
                    customer_errors.append(ErrorType(
                        field="phone",
                        message="Phone number must be in format: +1234567890 or 123-456-7890"
                    ))

                if customer_errors:
                    errors.append(CustomerValidationError(
                        index=index,
                        errors=customer_errors
                    ))
                    continue

                try:
                    customer = Customer.objects.create(
                        name=customer_data.name,
                        email=customer_data.email,
                        phone=customer_data.phone or ""
                    )
                    customers.append(customer)
                except IntegrityError:
                    errors.append(CustomerValidationError(
                        index=index,
                        errors=[ErrorType(field="email", message="Email already exists")]
                    ))
                except Exception as e:
                    errors.append(CustomerValidationError(
                        index=index,
                        errors=[ErrorType(field="general", message=str(e))]
                    ))

        return BulkCreateCustomers(customers=customers, errors=errors)


class CreateProduct(graphene.Mutation):
    class Arguments:
        input = ProductInput(required=True)

    product = graphene.Field(ProductType)
    message = graphene.String()
    errors = graphene.List(ErrorType)

    def mutate(self, info, input):
        errors = []

        # Validate price is positive
        if input.price <= 0:
            errors.append(ErrorType(field="price", message="Price must be positive"))

        # Validate stock is not negative
        if input.stock is not None and input.stock < 0:
            errors.append(ErrorType(field="stock", message="Stock cannot be negative"))

        if errors:
            return CreateProduct(errors=errors, message="Validation failed")

        try:
            product = Product.objects.create(
                name=input.name,
                price=input.price,
                stock=input.stock or 0
            )
            return CreateProduct(
                product=product,
                message=f"Product '{product.name}' created successfully"
            )
        except Exception as e:
            return CreateProduct(
                errors=[ErrorType(field="general", message=str(e))],
                message="Failed to create product"
            )


class CreateOrder(graphene.Mutation):
    class Arguments:
        input = OrderInput(required=True)

    order = graphene.Field(OrderType)
    message = graphene.String()
    errors = graphene.List(ErrorType)

    def mutate(self, info, input):
        errors = []

        # Validate customer exists
        try:
            customer = Customer.objects.get(id=input.customer_id)
        except Customer.DoesNotExist:
            errors.append(ErrorType(field="customer_id", message="Invalid customer ID"))
            return CreateOrder(errors=errors, message="Validation failed")

        # Validate at least one product is selected
        if not input.product_ids:
            errors.append(ErrorType(field="product_ids", message="At least one product must be selected"))

        # Validate all product IDs exist
        product_ids = input.product_ids
        products = Product.objects.filter(id__in=product_ids)
        
        if len(products) != len(product_ids):
            invalid_ids = set(product_ids) - set(str(p.id) for p in products)
            errors.append(ErrorType(
                field="product_ids", 
                message=f"Invalid product IDs: {', '.join(invalid_ids)}"
            ))

        if errors:
            return CreateOrder(errors=errors, message="Validation failed")

        try:
            with transaction.atomic():
                order = Order.objects.create(
                    customer=customer,
                    order_date=input.order_date or timezone.now()
                )
                
                # Add products to the order
                order.products.set(products)
                
                # Calculate and save total amount
                order.calculate_total_amount()
                order.save()

            return CreateOrder(
                order=order,
                message=f"Order created successfully with total amount ${order.total_amount}"
            )
        except Exception as e:
            return CreateOrder(
                errors=[ErrorType(field="general", message=str(e))],
                message="Failed to create order"
            )



# Updated Query Class (combining your existing queries with filtering)
class Query(ObjectType):
    """GraphQL Query class with both original and filtered fields"""
    
    # Your existing queries
    hello = graphene.String()
    customers = graphene.List(CustomerType)
    products = graphene.List(ProductType)
    orders = graphene.List(OrderType)
    
    customer = graphene.Field(CustomerType, id=graphene.ID())
    product = graphene.Field(ProductType, id=graphene.ID())
    order = graphene.Field(OrderType, id=graphene.ID())
    
    # New filtered connection fields using django-filter
    all_customers = DjangoFilterConnectionField(
        CustomerType,
        filterset_class=CustomerFilter,
        description="Get all customers with optional filtering"
    )
    
    all_products = DjangoFilterConnectionField(
        ProductType,
        filterset_class=ProductFilter,
        description="Get all products with optional filtering"
    )
    
    all_orders = DjangoFilterConnectionField(
        OrderType,
        filterset_class=OrderFilter,
        description="Get all orders with optional filtering"
    )
    
    # Individual item queries for relay
    customer_node = relay.Node.Field(CustomerType)
    product_node = relay.Node.Field(ProductType)
    order_node = relay.Node.Field(OrderType)
    
    # Custom filtered queries with ordering support
    filtered_customers = Field(
        graphene.List(CustomerType),
        filter=CustomerFilterInput(),
        order_by=String(description="Sort by field (prefix with - for descending)")
    )
    
    filtered_products = Field(
        graphene.List(ProductType),
        filter=ProductFilterInput(),
        order_by=String(description="Sort by field (prefix with - for descending)")
    )
    
    filtered_orders = Field(
        graphene.List(OrderType),
        filter=OrderFilterInput(),
        order_by=String(description="Sort by field (prefix with - for descending)")
    )

    # Your existing resolvers
    def resolve_hello(self, info):
        return "Hello, GraphQL CRM!"

    def resolve_customers(self, info):
        return Customer.objects.all()

    def resolve_products(self, info):
        return Product.objects.all()

    def resolve_orders(self, info):
        return Order.objects.all()

    def resolve_customer(self, info, id):
        try:
            return Customer.objects.get(id=id)
        except Customer.DoesNotExist:
            return None

    def resolve_product(self, info, id):
        try:
            return Product.objects.get(id=id)
        except Product.DoesNotExist:
            return None

    def resolve_order(self, info, id):
        try:
            return Order.objects.get(id=id)
        except Order.DoesNotExist:
            return None
    return bool(re.match(pattern, phone))


def validate_email_unique(email, exclude_id=None):
    """Check if email is unique"""
    queryset = Customer.objects.filter(email=email)
    if exclude_id:
        queryset = queryset.exclude(id=exclude_id)
    return not queryset.exists()


# Custom input types for filtering
class CustomerFilterInput(graphene.InputObjectType):
    """Input type for customer filtering"""
    name_icontains = String(description="Case-insensitive partial match for customer name")
    email_icontains = String(description="Case-insensitive partial match for customer email")
    created_at_gte = Date(description="Created after this date")
    created_at_lte = Date(description="Created before this date")
    phone_pattern = String(description="Filter by phone number pattern")


class ProductFilterInput(graphene.InputObjectType):
    """Input type for product filtering"""
    name_icontains = String(description="Case-insensitive partial match for product name")
    price_gte = Float(description="Minimum price")
    price_lte = Float(description="Maximum price")
    stock_gte = Int(description="Minimum stock quantity")
    stock_lte = Int(description="Maximum stock quantity")
    low_stock = Boolean(description="Filter products with low stock (< 10)")


class OrderFilterInput(graphene.InputObjectType):
    """Input type for order filtering"""
    total_amount_gte = Float(description="Minimum total amount")
    total_amount_lte = Float(description="Maximum total amount")
    order_date_gte = Date(description="Orders after this date")
    order_date_lte = Date(description="Orders before this date")
    customer_name = String(description="Filter by customer name")
    product_name = String(description="Filter by product name")
    product_id = Int(description="Filter orders by specific product ID")


class Query(ObjectType):
    """GraphQL Query class with filtered fields"""
    
    # Filtered connection fields using django-filter
    all_customers = DjangoFilterConnectionField(
        CustomerType,
        filterset_class=CustomerFilter,
        description="Get all customers with optional filtering"
    )
    
    all_products = DjangoFilterConnectionField(
        ProductType,
        filterset_class=ProductFilter,
        description="Get all products with optional filtering"
    )
    
    all_orders = DjangoFilterConnectionField(
        OrderType,
        filterset_class=OrderFilter,
        description="Get all orders with optional filtering"
    )
    
    # Individual item queries
    customer = relay.Node.Field(CustomerType)
    product = relay.Node.Field(ProductType)
    order = relay.Node.Field(OrderType)
    
    # Custom filtered queries with ordering support
    customers = Field(
        graphene.List(CustomerType),
        filter=CustomerFilterInput(),
        order_by=String(description="Sort by field (prefix with - for descending)")
    )
    
    products = Field(
        graphene.List(ProductType),
        filter=ProductFilterInput(),
        order_by=String(description="Sort by field (prefix with - for descending)")
    )
    
    orders = Field(
        graphene.List(OrderType),
        filter=OrderFilterInput(),
        order_by=String(description="Sort by field (prefix with - for descending)")
    )
    
    def resolve_customers(self, info, filter=None, order_by=None):
        """Resolve customers query with custom filtering and ordering"""
        queryset = Customer.objects.all()
        
        if filter:
            if filter.get('name_icontains'):
                queryset = queryset.filter(name__icontains=filter['name_icontains'])
            if filter.get('email_icontains'):
                queryset = queryset.filter(email__icontains=filter['email_icontains'])
            if filter.get('created_at_gte'):
                queryset = queryset.filter(created_at__gte=filter['created_at_gte'])
            if filter.get('created_at_lte'):
                queryset = queryset.filter(created_at__lte=filter['created_at_lte'])
            if filter.get('phone_pattern'):
                queryset = queryset.filter(phone__startswith=filter['phone_pattern'])
        
        if order_by:
            queryset = queryset.order_by(order_by)
        
        return queryset
    
    def resolve_products(self, info, filter=None, order_by=None):
        """Resolve products query with custom filtering and ordering"""
        queryset = Product.objects.all()
        
        if filter:
            if filter.get('name_icontains'):
                queryset = queryset.filter(name__icontains=filter['name_icontains'])
            if filter.get('price_gte'):
                queryset = queryset.filter(price__gte=filter['price_gte'])
            if filter.get('price_lte'):
                queryset = queryset.filter(price__lte=filter['price_lte'])
            if filter.get('stock_gte'):
                queryset = queryset.filter(stock__gte=filter['stock_gte'])
            if filter.get('stock_lte'):
                queryset = queryset.filter(stock__lte=filter['stock_lte'])
            if filter.get('low_stock'):
                queryset = queryset.filter(stock__lt=10)
        
        if order_by:
            queryset = queryset.order_by(order_by)
        
        return queryset
    
    def resolve_orders(self, info, filter=None, order_by=None):
        """Resolve orders query with custom filtering and ordering"""
        queryset = Order.objects.select_related('customer', 'product').all()
        
        if filter:
            if filter.get('total_amount_gte'):
                queryset = queryset.filter(total_amount__gte=filter['total_amount_gte'])
            if filter.get('total_amount_lte'):
                queryset = queryset.filter(total_amount__lte=filter['total_amount_lte'])
            if filter.get('order_date_gte'):
                queryset = queryset.filter(order_date__gte=filter['order_date_gte'])
            if filter.get('order_date_lte'):
                queryset = queryset.filter(order_date__lte=filter['order_date_lte'])
            if filter.get('customer_name'):
                queryset = queryset.filter(customer__name__icontains=filter['customer_name'])
            if filter.get('product_name'):
                queryset = queryset.filter(product__name__icontains=filter['product_name'])
            if filter.get('product_id'):
                queryset = queryset.filter(product__id=filter['product_id'])
        
        if order_by:
            queryset = queryset.order_by(order_by)
        
        return queryset
    
    # New custom filtered resolvers
    def resolve_filtered_customers(self, info, filter=None, order_by=None):
        """Resolve filtered customers query with custom filtering and ordering"""
        queryset = Customer.objects.all()
        
        if filter:
            if filter.get('name_icontains'):
                queryset = queryset.filter(name__icontains=filter['name_icontains'])
            if filter.get('email_icontains'):
                queryset = queryset.filter(email__icontains=filter['email_icontains'])
            if filter.get('created_at_gte'):
                queryset = queryset.filter(created_at__gte=filter['created_at_gte'])
            if filter.get('created_at_lte'):
                queryset = queryset.filter(created_at__lte=filter['created_at_lte'])
            if filter.get('phone_pattern'):
                queryset = queryset.filter(phone__startswith=filter['phone_pattern'])
        
        if order_by:
            queryset = queryset.order_by(order_by)
        
        return queryset
    
    def resolve_filtered_products(self, info, filter=None, order_by=None):
        """Resolve filtered products query with custom filtering and ordering"""
        queryset = Product.objects.all()
        
        if filter:
            if filter.get('name_icontains'):
                queryset = queryset.filter(name__icontains=filter['name_icontains'])
            if filter.get('price_gte'):
                queryset = queryset.filter(price__gte=filter['price_gte'])
            if filter.get('price_lte'):
                queryset = queryset.filter(price__lte=filter['price_lte'])
            if filter.get('stock_gte'):
                queryset = queryset.filter(stock__gte=filter['stock_gte'])
            if filter.get('stock_lte'):
                queryset = queryset.filter(stock__lte=filter['stock_lte'])
            if filter.get('low_stock'):
                queryset = queryset.filter(stock__lt=10)
        
        if order_by:
            queryset = queryset.order_by(order_by)
        
        return queryset
    
    def resolve_filtered_orders(self, info, filter=None, order_by=None):
        """Resolve filtered orders query with custom filtering and ordering"""
        queryset = Order.objects.select_related('customer').all()
        
        if filter:
            if filter.get('total_amount_gte'):
                queryset = queryset.filter(total_amount__gte=filter['total_amount_gte'])
            if filter.get('total_amount_lte'):
                queryset = queryset.filter(total_amount__lte=filter['total_amount_lte'])
            if filter.get('order_date_gte'):
                queryset = queryset.filter(order_date__gte=filter['order_date_gte'])
            if filter.get('order_date_lte'):
                queryset = queryset.filter(order_date__lte=filter['order_date_lte'])
            if filter.get('customer_name'):
                queryset = queryset.filter(customer__name__icontains=filter['customer_name'])
            # Note: For product filtering, you may need to adjust based on your Order model structure
            # if filter.get('product_name'):
            #     queryset = queryset.filter(products__name__icontains=filter['product_name'])
            # if filter.get('product_id'):
            #     queryset = queryset.filter(products__id=filter['product_id'])
        
        if order_by:
            queryset = queryset.order_by(order_by)
        
        return queryset


# Mutation Class (from your existing schema)
class Mutation(graphene.ObjectType):
    create_customer = CreateCustomer.Field()
    bulk_create_customers = BulkCreateCustomers.Field()
    create_product = CreateProduct.Field()
    create_order = CreateOrder.Field()


# Create schema
schema = graphene.Schema(query=Query, mutation=Mutation)