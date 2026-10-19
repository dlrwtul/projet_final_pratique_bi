with source as (

    select * from {{ source('bronze', 'Cities') }}

),


renamed as (

    select city_id, city_name, state_province_id, latest_recorded_population
    from source
)

select * from renamed

