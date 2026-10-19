select
    c.customer_id,
    c.customer_name,
    ci.city_name as delivery_city,
    c.credit_limit,
    c.account_opened_date
from {{ ref('stg_customers') }} c
left join {{ ref('stg_cities') }} ci on c.delivery_city_id = ci.city_id