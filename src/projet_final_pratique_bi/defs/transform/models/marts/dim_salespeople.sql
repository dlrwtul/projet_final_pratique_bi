select person_id as salesperson_id, full_name as salesperson_name, email_address
from {{ ref('stg_people') }}
where is_salesperson