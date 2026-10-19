# Guide pas à pas — Modern Data Platform WWI (DuckDB → Snowflake)

Rappel de la consigne (Projet_MDP_AI.pdf) :

```
SQL Server (WWI) --DLT--> BRONZE --dbt--> SILVER --dbt--> GOLD --Cortex AI--> Streamlit (Text-to-SQL)
                         \_________________ orchestré par Dagster _________________/
```

| Brique | Statut | Commentaire |
|---|---|---|
| SQL Server + WideWorldImporters | ✅ | Base restaurée, accessible en `mssql+pymssql` |
| Projet Dagster (`create-dagster`) | ✅ | Captures 1-2 |
| Ingestion DLT → Bronze (DuckDB) | ✅ (à corriger) | 6 tables chargées (captures 6-7) |
| Silver (staging dbt) | ⚠️ | Les modèles actuels **ne compilent pas** (voir étape 1) |
| Gold (marts dbt) | ❌ | Dossier `marts/` absent |
| Tests / doc dbt | ❌ | Aucun `schema.yml` |
| dbt branché dans Dagster | ❌ | Pas de `defs.yaml` dans `transform/` |
| Planification Dagster | ❌ | Aucun job / schedule |
| Bascule Snowflake | ❌ | Profil `prod` prêt mais non testé |
| Streamlit + Cortex AI | ❌ | Rien encore |
| Rapport | ❌ | Voir `docs/PLAN_RAPPORT.md` |

---

## ⚠️ Étape 0 — Sécurité (à faire tout de suite)

`captures/Capture5.png` montre en clair le mot de passe `sa` de SQL Server **et** le mot de passe Snowflake, et cette image est commitée sur GitHub.

1. Changez les deux mots de passe (SQL Server `sa` et l'utilisateur Snowflake).
2. Supprimez ou floutez `Capture5.png` (elle reste dans l'historique git : si le dépôt est public, considérez ces mots de passe comme compromis).
3. Le dossier `.dlt/` est bien ignoré par `.gitignore` (`*.dlt`), c'est correct ; ne commitez jamais `secrets.toml`.
4. Évitez d'utiliser `sa` : créez un login SQL en lecture seule pour DLT.

---

## Étape 1 — Corriger la couche Bronze (DLT)

### 1.1 Ce qu'il faut savoir

DLT **renomme** tables et colonnes en `snake_case` (vérifié) :

| SQL Server | Bronze (DuckDB / Snowflake) |
|---|---|
| `Sales.OrderLines` | `bronze.order_lines` |
| `Warehouse.StockItems` | `bronze.stock_items` |
| `CustomerID` | `customer_id` |
| `LastEditedWhen` | `last_edited_when` |

Il ajoute aussi `_dlt_load_id` et `_dlt_id`. C'est pour ça que vos modèles dbt (`select CustomerID ...`, `source('bronze','OrderLines')`) ne marcheront pas.

### 1.2 Fichier de la base DuckDB partagé entre DLT et dbt

Aujourd'hui DLT écrit dans `mssql_bronze.duckdb` (nom du pipeline) et dbt lit `dev.duckdb` → ce ne sont **pas** les mêmes fichiers. Utilisez un seul fichier, `warehouse.duckdb`, à la racine du projet.

### 1.3 `loads.py` corrigé

```python
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
        excluded_columns=["DeliveryLocation"],  # type geography non supporté
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
    # Recommandé : nécessaires pour la question « produits qui génèrent le plus de bénéfices »
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
        excluded_columns=["Location"],  # type geography non supporté
    )
    # Optionnel : pour analyser par région / pays
    yield sql_table(credentials=credentials, schema="Application", table="StateProvinces",
                    write_disposition="replace", excluded_columns=["Border"])
    yield sql_table(credentials=credentials, schema="Application", table="Countries",
                    write_disposition="replace", excluded_columns=["Border"])
    yield sql_table(
        credentials=credentials, schema="Application", table="People",
        write_disposition="replace",
        excluded_columns=["HashedPassword", "Photo"],  # données sensibles inutiles
    )


mssql_source = wwi_source()

if DEST == "duckdb":
    destination = dlt.destinations.duckdb(os.getenv("DUCKDB_PATH", "warehouse.duckdb"))
else:
    destination = "snowflake"

mssql_pipeline = dlt.pipeline(
    pipeline_name="mssql_bronze",
    destination=destination,
    dataset_name="bronze",
)
```

> Les `excluded_columns` suppriment les warnings `geography` des captures 6-7.
> `secrets.toml` doit être dans `.dlt/` **à la racine du projet** (là où vous lancez `dg dev`), pas seulement dans `defs/mssql_ingestion/.dlt/`.

Test :

```bash
DLT_DESTINATION=duckdb python src/projet_final_pratique_bi/defs/mssql_ingestion/loads.py   # ou via Dagster
python -c "import duckdb; print(duckdb.connect('warehouse.duckdb').sql('show all tables'))"
```

---

## Étape 2 — Couche Silver (dbt staging)

### 2.1 Ranger le projet dbt

- Supprimez le `dbt_project.yml` **à la racine** (doublon de `src/.../transform/dbt_project.yml`).
- Déplacez `.dbt/profiles.yml` dans `src/projet_final_pratique_bi/defs/transform/profiles.yml`.

`profiles.yml` :

```yaml
transform:
  target: "{{ env_var('DBT_TARGET', 'dev') }}"
  outputs:
    dev:
      type: duckdb
      path: "{{ env_var('DUCKDB_PATH') }}"   # chemin ABSOLU, le même que pour DLT
      schema: main
      threads: 4
    prod:
      type: snowflake
      account: "{{ env_var('SF_ACCOUNT') }}"
      user: "{{ env_var('SF_USER') }}"
      password: "{{ env_var('SF_PASSWORD') }}"
      role: PFPB_ROLE
      warehouse: WH_TRANSFORM
      database: PROJET_FINAL_PRATIQUE_BI
      schema: SILVER
      threads: 4
```

> Faites `export DUCKDB_PATH=$HOME/projet_final_pratique_bi/warehouse.duckdb` (dans `~/.bashrc` ou un `.env`) : DLT et dbt pointent alors sur le même fichier quel que soit le dossier courant.

### 2.2 Macro de nommage des schémas

Sans elle, dbt crée `main_silver` (DuckDB) ou `SILVER_SILVER` (Snowflake). Créez `transform/macros/generate_schema_name.sql` :

```sql
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
```

### 2.3 `models/_sources.yml`

On garde les noms `Customers`, `OrderLines`… (ainsi les clés d'assets dbt `bronze/Customers` correspondent exactement à celles de DLT → Dagster relie automatiquement Bronze → Silver), et on pointe vers la vraie table avec `identifier`. On retire `database:` (en dur, il casse DuckDB).

```yaml
version: 2

sources:
  - name: bronze
    schema: bronze
    tables:
      - name: Customers
        identifier: customers
      - name: Orders
        identifier: orders
      - name: OrderLines
        identifier: order_lines
      - name: Invoices
        identifier: invoices
      - name: InvoiceLines
        identifier: invoice_lines
      - name: StockItems
        identifier: stock_items
      - name: Cities
        identifier: cities
      - name: People
        identifier: people
```

### 2.4 Modèles staging (nettoyage, typage, règles métier)

Renommez les fichiers en snake_case (`stg_order_lines.sql`, `stg_stock_items.sql`) et corrigez les fautes actuelles (`OderID as oeder_id`, `delivery_city_iD`).

`stg_customers.sql`
```sql
select
    customer_id,
    trim(customer_name)               as customer_name,
    primary_contact_person_id         as contact_person_id,
    delivery_city_id,
    customer_category_id,
    credit_limit,
    cast(account_opened_date as date) as account_opened_date,
    phone_number,
    delivery_postal_code
from {{ source('bronze', 'Customers') }}
```

`stg_orders.sql`
```sql
select
    order_id,
    customer_id,
    salesperson_person_id,
    contact_person_id,
    cast(order_date as date)             as order_date,
    cast(expected_delivery_date as date) as expected_delivery_date
from {{ source('bronze', 'Orders') }}
```

`stg_order_lines.sql`
```sql
select
    order_line_id,
    order_id,
    stock_item_id,
    description,
    quantity,
    unit_price,
    tax_rate,
    picked_quantity
from {{ source('bronze', 'OrderLines') }}
where quantity > 0
```

`stg_invoice_lines.sql` (pour le bénéfice)
```sql
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
from {{ source('bronze', 'InvoiceLines') }} il
join {{ source('bronze', 'Invoices') }} i on il.invoice_id = i.invoice_id
```

`stg_stock_items.sql`
```sql
select
    stock_item_id,
    trim(stock_item_name)  as stock_item_name,
    coalesce(brand, 'N/A') as brand,
    unit_price,
    recommended_retail_price,
    tax_rate
from {{ source('bronze', 'StockItems') }}
```

`stg_cities.sql`
```sql
select city_id, city_name, state_province_id, latest_recorded_population
from {{ source('bronze', 'Cities') }}
```

`stg_people.sql` — gardez **toutes** les personnes en Silver (les contacts clients en ont besoin) ; le filtre vendeur se fait en Gold.
```sql
select person_id, full_name, preferred_name, is_salesperson, is_employee, email_address
from {{ source('bronze', 'People') }}
```

### 2.5 Tests de qualité — `models/staging/_staging.yml`

```yaml
version: 2

models:
  - name: stg_customers
    description: "Clients nettoyés"
    columns:
      - name: customer_id
        data_tests: [unique, not_null]
  - name: stg_orders
    columns:
      - name: order_id
        data_tests: [unique, not_null]
      - name: customer_id
        data_tests:
          - not_null
          - relationships:
              arguments:
                to: ref('stg_customers')
                field: customer_id
  - name: stg_order_lines
    columns:
      - name: order_line_id
        data_tests: [unique, not_null]
  - name: stg_stock_items
    columns:
      - name: stock_item_id
        data_tests: [unique, not_null]
  - name: stg_people
    columns:
      - name: person_id
        data_tests: [unique, not_null]
```

Test : `cd src/projet_final_pratique_bi/defs/transform && dbt build --profiles-dir .`

---

## Étape 3 — Couche Gold (schéma en étoile)

Dossier `models/marts/` (déjà configuré en `table` / schéma `gold` dans `dbt_project.yml`).

| Modèle | Rôle |
|---|---|
| `dim_customers` | client + ville de livraison |
| `dim_products` | articles (stock items) |
| `dim_salespeople` | vendeurs (`is_salesperson = true`) |
| `dim_date` | calendrier (année, trimestre, mois) |
| `fct_sales` | fait ventes, grain = ligne de commande |
| `fct_invoice_lines` | fait facturation avec `line_profit` (bénéfice) |

`dim_customers.sql`
```sql
select
    c.customer_id,
    c.customer_name,
    ci.city_name as delivery_city,
    c.credit_limit,
    c.account_opened_date
from {{ ref('stg_customers') }} c
left join {{ ref('stg_cities') }} ci on c.delivery_city_id = ci.city_id
```

`dim_products.sql`
```sql
select stock_item_id as product_id, stock_item_name as product_name, brand,
       unit_price, recommended_retail_price
from {{ ref('stg_stock_items') }}
```

`dim_salespeople.sql`
```sql
select person_id as salesperson_id, full_name as salesperson_name, email_address
from {{ ref('stg_people') }}
where is_salesperson
```

`dim_date.sql`
```sql
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
```

`fct_sales.sql`
```sql
select
    ol.order_line_id,
    o.order_id,
    o.order_date,
    o.customer_id,
    o.salesperson_person_id     as salesperson_id,
    ol.stock_item_id            as product_id,
    ol.quantity,
    ol.unit_price,
    ol.quantity * ol.unit_price as sales_amount_excl_tax,
    ol.quantity * ol.unit_price * (1 + ol.tax_rate / 100) as sales_amount_incl_tax
from {{ ref('stg_order_lines') }} ol
join {{ ref('stg_orders') }} o on ol.order_id = o.order_id
```

`fct_invoice_lines.sql`
```sql
select
    invoice_line_id, invoice_id, invoice_date, customer_id,
    salesperson_person_id as salesperson_id,
    stock_item_id as product_id,
    quantity, extended_price, tax_amount, line_profit
from {{ ref('stg_invoice_lines') }}
```

`models/marts/_marts.yml` (tests + **descriptions** : elles serviront aussi de contexte à Cortex AI)

```yaml
version: 2

models:
  - name: fct_sales
    description: "Ventes, une ligne par ligne de commande"
    columns:
      - name: order_line_id
        data_tests: [unique, not_null]
      - name: sales_amount_excl_tax
        description: "Chiffre d'affaires HT = quantity * unit_price"
      - name: product_id
        data_tests:
          - relationships:
              arguments: {to: ref('dim_products'), field: product_id}
      - name: customer_id
        data_tests:
          - relationships:
              arguments: {to: ref('dim_customers'), field: customer_id}
  - name: fct_invoice_lines
    description: "Lignes facturées ; line_profit = bénéfice de la ligne"
    columns:
      - name: invoice_line_id
        data_tests: [unique, not_null]
```

Puis : `dbt build --profiles-dir .` et `dbt docs generate --profiles-dir . && dbt docs serve` (capture du lineage pour le rapport).

> J'ai validé cette chaîne Bronze → Silver → Gold sur DuckDB avec des données de test : 27/27 modèles + tests OK (hors tables Invoices, à vérifier sur vos vraies données).

---

## Étape 4 — Orchestration Dagster

### 4.1 Brancher dbt

`src/projet_final_pratique_bi/defs/transform/defs.yaml` :

```yaml
type: dagster_dbt.DbtProjectComponent

attributes:
  project:
    project_dir: "{{ context.project_root }}/src/projet_final_pratique_bi/defs/transform"
    profiles_dir: "{{ context.project_root }}/src/projet_final_pratique_bi/defs/transform"
  cli_args:
    - build
```

### 4.2 Job + planification

`src/projet_final_pratique_bi/defs/schedules.py` :

```python
import dagster as dg

pipeline_complet = dg.define_asset_job(name="pipeline_complet", selection="*")

schedule_quotidien = dg.ScheduleDefinition(
    job=pipeline_complet,
    cron_schedule="0 2 * * *",
    execution_timezone="Africa/Dakar",
)
```

### 4.3 Vérifier

```bash
dg check defs
dg list defs        # vous devez voir bronze/*, silver/stg_*, gold/*, le job et le schedule
dg dev              # http://localhost:3000 → Global Asset Lineage → Materialize all
```

Captures pour le rapport : lineage complet, un run réussi, les asset checks (tests dbt), le schedule activé.

> DuckDB n'accepte qu'un seul écrivain : fermez DBeaver/notebook sur `warehouse.duckdb` pendant un run.

---

## Étape 5 — Bascule vers Snowflake

### 5.1 Préparer Snowflake (worksheet, en ACCOUNTADMIN)

```sql
CREATE ROLE IF NOT EXISTS PFPB_ROLE;
CREATE WAREHOUSE IF NOT EXISTS WH_TRANSFORM WAREHOUSE_SIZE = XSMALL AUTO_SUSPEND = 60 AUTO_RESUME = TRUE;
CREATE DATABASE IF NOT EXISTS PROJET_FINAL_PRATIQUE_BI;
CREATE SCHEMA IF NOT EXISTS PROJET_FINAL_PRATIQUE_BI.BRONZE;
CREATE SCHEMA IF NOT EXISTS PROJET_FINAL_PRATIQUE_BI.SILVER;
CREATE SCHEMA IF NOT EXISTS PROJET_FINAL_PRATIQUE_BI.GOLD;

GRANT USAGE ON WAREHOUSE WH_TRANSFORM TO ROLE PFPB_ROLE;
GRANT ALL ON DATABASE PROJET_FINAL_PRATIQUE_BI TO ROLE PFPB_ROLE;
GRANT ALL ON ALL SCHEMAS IN DATABASE PROJET_FINAL_PRATIQUE_BI TO ROLE PFPB_ROLE;
GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE PFPB_ROLE;   -- pour Cortex AI
GRANT ROLE PFPB_ROLE TO USER LANG;
```

Utilisez **le même** warehouse partout (aujourd'hui `secrets.toml` dit `COMPUTE_WH` et `profiles.yml` dit `WH_TRANSFORM`).

### 5.2 Lancer en mode Snowflake

```bash
export DLT_DESTINATION=snowflake
export DBT_TARGET=prod
export SF_ACCOUNT=xxxxx-yyyyy SF_USER=lang SF_PASSWORD='...'
dg dev
```

Rien d'autre à changer : Snowflake met les identifiants non quotés en majuscules, donc `bronze.customers` → `BRONZE.CUSTOMERS`, et la macro donne bien `SILVER` / `GOLD`. Vérifiez dans Snowsight que les 3 schémas sont remplis.

---

## Étape 6 — Application Streamlit + Cortex AI (Text-to-SQL)

`uv add streamlit snowflake-connector-python pandas`, puis `streamlit_app/app.py` :

```python
import os
import re

import pandas as pd
import snowflake.connector
import streamlit as st

MODEL = "mistral-large2"  # ou llama3.1-70b selon votre région Snowflake


@st.cache_resource
def get_conn():
    return snowflake.connector.connect(
        account=os.environ["SF_ACCOUNT"], user=os.environ["SF_USER"],
        password=os.environ["SF_PASSWORD"], role="PFPB_ROLE",
        warehouse="WH_TRANSFORM", database="PROJET_FINAL_PRATIQUE_BI", schema="GOLD",
    )


@st.cache_data(ttl=3600)
def gold_schema() -> str:
    df = pd.read_sql(
        "select table_name, column_name, data_type from information_schema.columns "
        "where table_schema = 'GOLD' order by table_name, ordinal_position",
        get_conn(),
    )
    return "\n".join(
        f"GOLD.{t}({', '.join(f'{c} {d}' for c, d in zip(g.COLUMN_NAME, g.DATA_TYPE))})"
        for t, g in df.groupby("TABLE_NAME")
    )


def generate_sql(question: str) -> str:
    prompt = f"""Tu es un expert Snowflake SQL. Schéma disponible :
{gold_schema()}

Règles : une seule requête SELECT, uniquement les tables GOLD ci-dessus,
chiffre d'affaires = SUM(sales_amount_excl_tax) de fct_sales,
bénéfice = SUM(line_profit) de fct_invoice_lines, LIMIT 1000 maximum.
Réponds uniquement avec le SQL, sans explication.

Question : {question}"""
    cur = get_conn().cursor()
    cur.execute("select snowflake.cortex.complete(%s, %s)", (MODEL, prompt))
    sql = cur.fetchone()[0]
    return re.sub(r"```(sql)?", "", sql).strip().rstrip(";")


st.title("Wide World Importers — posez votre question")
question = st.text_input("Question", "Quels sont les dix meilleurs clients par chiffre d'affaires ?")

if st.button("Interroger") and question:
    sql = generate_sql(question)
    st.code(sql, language="sql")
    if not sql.lower().lstrip().startswith(("select", "with")):
        st.error("Requête refusée : seules les requêtes SELECT sont autorisées.")
    else:
        df = pd.read_sql(sql, get_conn())
        st.dataframe(df)
        num = df.select_dtypes("number").columns
        if len(df.columns) >= 2 and len(num):
            st.bar_chart(df.set_index(df.columns[0])[num[0]])
```

Lancer : `streamlit run streamlit_app/app.py`.

Sécurité à mentionner dans le rapport : rôle Snowflake en **lecture seule** sur GOLD pour l'app, refus de tout ce qui n'est pas `SELECT`, `LIMIT`.

Tester (et capturer) les 3 questions de la consigne :
1. « Quels sont les dix meilleurs clients par chiffre d'affaires ? »
2. « Quel est le montant total des ventes par mois ? »
3. « Quels produits génèrent le plus de bénéfices ? »

Bonus : Cortex Analyst avec un *semantic model* YAML (plus fiable que le prompt brut) — à citer en perspective.

---

## Étape 7 — Finitions

- `README.md` : remplacer le texte du template par : architecture, installation, variables d'environnement, commandes.
- `.env.example` (sans vrais secrets) avec `DLT_DESTINATION`, `DBT_TARGET`, `DUCKDB_PATH`, `SF_*`.
- Ajouter `*.duckdb` au `.gitignore`.
- Supprimer `logs/query_log.sql` (vide) et `.dbt/`.
- Faire les captures au fur et à mesure (elles iront dans le rapport).
- Rédiger le rapport : voir `docs/PLAN_RAPPORT.md`.

## Ordre conseillé

1. Étape 0 (sécurité) → 2. Étape 1 (Bronze) → 3. Étapes 2-3 (dbt, sur DuckDB) → 4. Étape 4 (Dagster, sur DuckDB) → 5. Étape 5 (Snowflake) → 6. Étape 6 (Streamlit/Cortex, Snowflake obligatoire) → 7. Rapport.
