select
    ol.order_line_id,
    o.order_id,
    o.order_date,
    o.customer_id,
    o.salesperson_person_id     as salesperson_id,
    ol.stock_item_id            as product_id,
    ol.quantity,
    ol.unit_price,
    ol.quantity * ol.unit_price as sales_amount_excl_tax,
    ol.quantity * ol.unit_price * (1 + ol.tax_rate / 100) as sales_amount_incl_tax
from {{ ref('stg_order_lines') }} ol
join {{ ref('stg_orders') }} o on ol.order_id = o.order_id