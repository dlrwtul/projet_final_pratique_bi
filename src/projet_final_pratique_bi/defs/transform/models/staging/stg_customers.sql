with source as (

    select * from {{ source('bronze', 'Customers') }}

),


renamed as (

    select
        CustomerID    as customer_id,

        CustomerName    as customer_name,

        PrimaryContactPersonID  as person_id,

        DeliveryCityID  as delivery_city_iD,

        CreditLimit as credit_limit,

        AccountOpenedDate as account_opened_date,

        PhoneNumber as phone_number,

        FaxNumber as fax_number,

        DeliveryAddressLine1 as delivery_address_line1,

        DeliveryAddressLine2 as delivery_address_line2,

        DeliveryPostalCode  as delivery_postal_code,

        PostalAddressLine1 as postal_address_line1,

        PostalAddressLine2 as postal_address_line2,

        PostalPostalCode    as postal_postal_code

    from source
)

select * from renamed

