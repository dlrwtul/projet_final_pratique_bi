with source as (

    select * from {{ source('bronze', 'OrderLines') }}

),


renamed as (

    select
    order_line_id,
    order_id,
    stock_item_id,
    description,
    quantity,
    unit_price,
    tax_rate,
    picked_quantity
    from source
    where quantity > 0
)

select * from renamed

