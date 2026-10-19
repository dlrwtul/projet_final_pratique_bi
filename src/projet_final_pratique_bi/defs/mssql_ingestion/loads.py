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
        excluded_columns=["DeliveryLocation"],
    )
    yield sql_table(
        credentials=credentials, schema="Sales", table="Orders",
        write_disposition="merge", primary_key="OrderID",
        incremental=dlt.sources.incremental("LastEditedWhen"),
    )
    yield sql_table(
        credentials=credentials, schema="Sales", table="OrderLines",
        write_disposition="merge", primary_key="OrderLineID",
        incremental=dlt.sources.incremental("LastEditedWhen"),
    )
    yield sql_table(
        credentials=credentials, schema="Sales", table="Invoices",
        write_disposition="merge", primary_key="InvoiceID",
        incremental=dlt.sources.incremental("LastEditedWhen"),
    )
    yield sql_table(
        credentials=credentials, schema="Sales", table="InvoiceLines",
        write_disposition="merge", primary_key="InvoiceLineID",
        incremental=dlt.sources.incremental("LastEditedWhen"),
    )
    yield sql_table(
        credentials=credentials, schema="Warehouse", table="StockItems",
        write_disposition="replace",
        excluded_columns=["Photo"],
    )
    yield sql_table(
        credentials=credentials, schema="Application", table="Cities",
        write_disposition="replace",
        excluded_columns=["Location"],
    )
    yield sql_table(credentials=credentials, schema="Application", table="StateProvinces",
                    write_disposition="replace", excluded_columns=["Border"])
    yield sql_table(credentials=credentials, schema="Application", table="Countries",
                    write_disposition="replace", excluded_columns=["Border"])
    yield sql_table(
        credentials=credentials, schema="Application", table="People",
        write_disposition="replace",
        excluded_columns=["HashedPassword", "Photo"],
    )


mssql_source = wwi_source()

if DEST == "duckdb":
    # expandvars/expanduser : un fichier .env (chargé par Dagster) ne remplace pas $HOME ni ~.
    duckdb_path = os.path.expanduser(os.path.expandvars(os.getenv("DUCKDB_PATH", "warehouse.duckdb")))
    destination = dlt.destinations.duckdb(duckdb_path)
else:
    destination = "snowflake"

mssql_pipeline = dlt.pipeline(
    pipeline_name="mssql_bronze",
    destination=destination,
    dataset_name="bronze",
)

if __name__ == "__main__":
    load_info = mssql_pipeline.run(mssql_source)
    print(load_info)