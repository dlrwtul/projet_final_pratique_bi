import os
import dlt
from dlt.sources.sql_database import sql_table

DEST = os.getenv("DLT_DESTINATION", "duckdb")

credentials = dlt.secrets.get("sources.sql_database.credentials")

@dlt.source(name="wwi")
def wwi_source():
    yield sql_table(
        credentials=credentials, schema="Sales", table="Customers",
        write_disposition="replace",
    )

    yield sql_table(
        credentials=credentials, schema="Sales", table="Orders",
        write_disposition="merge",
        primary_key="OrderID",
        incremental=dlt.sources.incremental("LastEditedWhen"),
    )

    yield sql_table(
        credentials=credentials, schema="Sales", table="OrderLines",
        write_disposition="merge",
        primary_key="OrderLineID",
        incremental=dlt.sources.incremental("LastEditedWhen"),
    )

    yield sql_table(
        credentials=credentials, schema="Warehouse", table="StockItems",
        write_disposition="replace",
    )

    yield sql_table(
        credentials=credentials, schema="Application", table="Cities",
        write_disposition="replace",
    )

    yield sql_table(
        credentials=credentials, schema="Application", table="People",
        write_disposition="replace",
    )

mssql_source = wwi_source()

mssql_pipeline = dlt.pipeline(
    pipeline_name="mssql_bronze",
    destination=DEST,
    dataset_name="bronze",
)