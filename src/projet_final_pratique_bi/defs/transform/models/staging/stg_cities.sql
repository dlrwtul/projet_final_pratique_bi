with source as (

    select * from {{ source('bronze', 'Cities') }}

),


renamed as (

    select
        CityID    as city_id,

        CityName    as city_name,

        Location  as location,

        LatestRecordedPopulation as latest_recorded_population

    from source
)

select * from renamed

