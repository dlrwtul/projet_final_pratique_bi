with days as (
    {{ dbt.date_spine(datepart="day",
        start_date="cast('2013-01-01' as date)",
        end_date="cast('2017-01-01' as date)") }}
)
select
    cast(date_day as date)         as date_day,
    extract(year from date_day)    as year,
    extract(quarter from date_day) as quarter,
    extract(month from date_day)   as month,
    extract(day from date_day)     as day
from days