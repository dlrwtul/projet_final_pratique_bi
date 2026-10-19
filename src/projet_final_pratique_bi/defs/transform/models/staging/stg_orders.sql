with source as (

    select * from {{ source('bronze', 'Orders') }}

),


renamed as (

    select
        OrderID    as order_id,

        CustomerID    as customer_id,

        ContactPersonID  as contact_person_id,

        OrderDate as order_date

    from source
)

select * from renamed

