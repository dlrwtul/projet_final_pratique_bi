with source as (

    select * from {{ source('bronze', 'StockItems') }}

),


renamed as (

    select
        StockItemID    as stock_item_id,

        StockItemName    as stock_item_name,

        UnitPrice as unit_price

    from source
)

select * from renamed

