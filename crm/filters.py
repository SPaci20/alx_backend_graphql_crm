# crm/filters.py
import django_filters
from django_filters import FilterSet, CharFilter, DateFromToRangeFilter, NumberFilter
from .models import Customer, Product, Order


class CustomerFilter(FilterSet):
    """Filter class for Customer model with name, email, and date range filtering"""
    name = CharFilter(field_name='name', lookup_expr='icontains', help_text="Case-insensitive partial match for customer name")
    email = CharFilter(field_name='email', lookup_expr='icontains', help_text="Case-insensitive partial match for customer email")
    created_at = DateFromToRangeFilter(field_name='created_at', help_text="Filter by creation date range")
    created_at__gte = django_filters.DateFilter(field_name='created_at', lookup_expr='gte', help_text="Created after this date")
    created_at__lte = django_filters.DateFilter(field_name='created_at', lookup_expr='lte', help_text="Created before this date")
    
    # Custom filter for phone number pattern (Challenge requirement)
    phone_pattern = CharFilter(method='filter_phone_pattern', help_text="Filter by phone number pattern (e.g., starts with +1)")
    
    def filter_phone_pattern(self, queryset, name, value):
        """Custom method to filter customers by phone number pattern"""
        if value:
            return queryset.filter(phone__startswith=value)
        return queryset
    
    class Meta:
        model = Customer
        fields = ['name', 'email', 'created_at', 'phone_pattern']


class ProductFilter(FilterSet):
    """Filter class for Product model with name, price, and stock filtering"""
    name = CharFilter(field_name='name', lookup_expr='icontains', help_text="Case-insensitive partial match for product name")
    price__gte = NumberFilter(field_name='price', lookup_expr='gte', help_text="Minimum price")
    price__lte = NumberFilter(field_name='price', lookup_expr='lte', help_text="Maximum price")
    stock__gte = NumberFilter(field_name='stock', lookup_expr='gte', help_text="Minimum stock quantity")
    stock__lte = NumberFilter(field_name='stock', lookup_expr='lte', help_text="Maximum stock quantity")
    stock = NumberFilter(field_name='stock', lookup_expr='exact', help_text="Exact stock quantity")
    
    # Custom filter for low stock (Challenge requirement)
    low_stock = django_filters.BooleanFilter(method='filter_low_stock', help_text="Filter products with low stock (< 10)")
    
    def filter_low_stock(self, queryset, name, value):
        """Custom method to filter products with low stock"""
        if value:
            return queryset.filter(stock__lt=10)
        return queryset
    
    class Meta:
        model = Product
        fields = ['name', 'price', 'stock', 'low_stock']


class OrderFilter(FilterSet):
    """Filter class for Order model with total amount, date, and related field filtering"""
    total_amount__gte = NumberFilter(field_name='total_amount', lookup_expr='gte', help_text="Minimum total amount")
    total_amount__lte = NumberFilter(field_name='total_amount', lookup_expr='lte', help_text="Maximum total amount")
    order_date__gte = django_filters.DateFilter(field_name='order_date', lookup_expr='gte', help_text="Orders after this date")
    order_date__lte = django_filters.DateFilter(field_name='order_date', lookup_expr='lte', help_text="Orders before this date")
    order_date = DateFromToRangeFilter(field_name='order_date', help_text="Filter by order date range")
    
    # Related field filters
    customer_name = CharFilter(field_name='customer__name', lookup_expr='icontains', help_text="Filter by customer name")
    product_name = CharFilter(field_name='product__name', lookup_expr='icontains', help_text="Filter by product name")
    
    # Challenge: Filter orders by specific product ID
    product_id = NumberFilter(field_name='product__id', lookup_expr='exact', help_text="Filter orders by specific product ID")
    
    class Meta:
        model = Order
        fields = ['total_amount', 'order_date', 'customer_name', 'product_name', 'product_id']