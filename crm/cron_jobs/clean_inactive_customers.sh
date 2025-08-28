#!/bin/bash

# Navigate to project root (assuming this script is inside crm/cron_jobs)
cd "$(dirname "$0")/../.."

# Run Django shell command to delete inactive customers
DELETED_COUNT=$(python3 manage.py shell -c "
import datetime
from crm.models import Customer, Order

one_year_ago = datetime.datetime.now() - datetime.timedelta(days=365)

inactive_customers = Customer.objects.exclude(
    id__in=Order.objects.filter(created_at__gte=one_year_ago).values_list('customer_id', flat=True)
)

count = inactive_customers.count()
inactive_customers.delete()
print(count)
")

# Log the result with timestamp
echo \"\$(date '+%Y-%m-%d %H:%M:%S') - Deleted \$DELETED_COUNT inactive customers\" >> /tmp/customer_cleanup_log.txt
