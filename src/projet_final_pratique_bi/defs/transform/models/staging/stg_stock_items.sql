with source as (

    select * from {{ source('bronze', 'StockItems') }}

),


renamed as (

    select
    stock_item_id,
    trim(stock_item_name)  as stock_item_name,
    coalesce(brand, 'N/A') as brand,
    unit_price,
    recommended_retail_price,
    tax_rate
    from source
)

select * from renamed

