with source as (

    select * from {{ source('bronze', 'OrderLines') }}

),


renamed as (

    select
        OrderLineID    as order_line_id,

        OderID    as oeder_id,

        StockItemID  as stock_item_id,

        Quantity as quantity,

        UnitPrice as unit_price

    from source

)

select * from renamed

