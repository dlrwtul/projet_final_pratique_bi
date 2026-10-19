with source as (

    select * from {{ source('bronze', 'People') }}

),


renamed as (

    select person_id, full_name, preferred_name, is_salesperson, is_employee, email_address
    from source
)

select * from renamed

