with source as (

    select * from {{ source('bronze', 'InvoiceLines') }}

),
source2 as (

    select * from {{ source('bronze', 'Invoices') }}

),


renamed as (

    select
    il.invoice_line_id,
    il.invoice_id,
    i.order_id,
    i.customer_id,
    i.salesperson_person_id,
    cast(i.invoice_date as date) as invoice_date,
    il.stock_item_id,
    il.quantity,
    il.unit_price,
    il.extended_price,
    il.tax_amount,
    il.line_profit
    from source il
    join source2 i on il.invoice_id = i.invoice_id
)

select * from renamed