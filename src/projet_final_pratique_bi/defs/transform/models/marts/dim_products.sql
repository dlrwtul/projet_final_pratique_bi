select stock_item_id as product_id, stock_item_name as product_name, brand,
       unit_price, recommended_retail_price
from {{ ref('stg_stock_items') }}