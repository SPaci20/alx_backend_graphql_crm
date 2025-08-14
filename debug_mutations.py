import graphene
from graphene_django import DjangoObjectType
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError
from django.utils import timezone
from decimal import Decimal
import re

from .models import Customer, Product, Order


# Object Types
class CustomerType(DjangoObjectType):
    class Meta:
        model = Customer
        fields = '__all__'


class ProductType(DjangoObjectType):
    class Meta:
        model = Product
        fields = '__all__'


class OrderType(DjangoObjectType):
    class Meta:
        model = Order
        fields = '__all__'


# Input Types
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


# Error Types
class ErrorType(graphene.ObjectType):
    field = graphene.String()
    message = graphene.String()


class CustomerValidationError(graphene.ObjectType):
    index = graphene.Int()
    errors = graphene.List(ErrorType)


# Mutation Output Types
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


# Utility Functions
def validate_phone(phone):
    """Validate phone number format"""
    if not phone:
        return True
    pattern = r'^\+?[\d\-\(\)\s]+$'
    return bool(re.match(pattern, phone))


def validate_email_unique(email, exclude_id=None):
    """Check if email is unique"""
    queryset = Customer.objects.filter(email=email)
    if exclude_id:
        queryset = queryset.exclude(id=exclude_id)
    return not queryset.exists()


# Mutations
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


# Query Class
class Query(graphene.ObjectType):
    hello = graphene.String()
    customers = graphene.List(CustomerType)
    products = graphene.List(ProductType)
    orders = graphene.List(OrderType)
    
    customer = graphene.Field(CustomerType, id=graphene.ID())
    product = graphene.Field(ProductType, id=graphene.ID())
    order = graphene.Field(OrderType, id=graphene.ID())

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


# Mutation Class
class Mutation(graphene.ObjectType):
    create_customer = CreateCustomer.Field()
    bulk_create_customers = BulkCreateCustomers.Field()
    create_product = CreateProduct.Field()
    create_order = CreateOrder.Field()