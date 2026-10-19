with source as (

    select * from {{ source('bronze', 'Customers') }}

),


renamed as (

    select
    customer_id,
    trim(customer_name)               as customer_name,
    primary_contact_person_id         as contact_person_id,
    delivery_city_id,
    customer_category_id,
    credit_limit,
    cast(account_opened_date as date) as account_opened_date,
    phone_number,
    delivery_postal_code
    from source
)

select * from renamed

