with source as (

    select * from {{ source('bronze', 'People') }}

),


renamed as (

    select
        PersonID    as person_id,

        FullName    as full_name,

        PreferredName  as preferred_name,

        SearchName as search_name,

        PhoneNumber as phone_number,

        FaxNumber   as  fax_number,

        EmailAddress    as  email_address

    from source

    where IsSalesperson = 1
)

select * from renamed

