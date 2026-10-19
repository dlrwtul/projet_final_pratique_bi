with source as (

    select * from {{ source('bronze', 'Orders') }}

),


renamed as (

    select
    order_id,
    customer_id,
    salesperson_person_id,
    contact_person_id,
    cast(order_date as date)             as order_date,
    cast(expected_delivery_date as date) as expected_delivery_date
    from source
)

select * from renamed

