select
    invoice_line_id, invoice_id, invoice_date, customer_id,
    salesperson_person_id as salesperson_id,
    stock_item_id as product_id,
    quantity, extended_price, tax_amount, line_profit
from {{ ref('stg_invoice_lines') }}