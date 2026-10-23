# Mise en œuvre

Le projet a été créé avec `create-dagster`, puis les dépendances ont été ajoutées avec `uv add` (DLT, dagster-dlt, dagster-dbt, dbt-snowflake, Streamlit…). Le composant d'ingestion a été généré avec `dg scaffold defs dagster_dlt.DltLoadCollectionComponent mssql_ingestion`, et le projet dbt est placé dans `defs/transform`.

## Ingestion avec DLT

Chaque table est déclarée dans `loads.py` comme une ressource de la source `wwi`. Voici les deux premières, les autres suivent le même modèle :

``` {.python #code:dlt caption="Source DLT (defs/mssql_ingestion/loads.py)"}
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
```

Les petites tables de référence sont rechargées entièrement (`replace`). Pour les commandes, les factures et leurs lignes, le chargement est incrémental : DLT retient la dernière valeur de `LastEditedWhen` et ne relit ensuite que les lignes modifiées, et `merge` évite les doublons grâce à la clé primaire. Les colonnes de type `geography` (comme `DeliveryLocation`) sont exclues parce que DLT ne sait pas les convertir ; au début elles provoquaient des avertissements à chaque chargement. Les identifiants SQL Server sont dans `.dlt/secrets.toml`, qui n'est pas versionné.

Un point qui nous a fait perdre du temps : DLT renomme les tables et les colonnes en snake_case (`OrderLines` devient `order_lines`, `CustomerID` devient `customer_id`). Nos premiers modèles dbt utilisaient les noms d'origine et ne trouvaient pas les tables. Dans les sources dbt, nous avons donc gardé le nom SQL Server comme nom logique et ajouté le vrai nom avec `identifier`. Cela permet aussi à Dagster de relier automatiquement les actifs DLT aux modèles dbt.

![Étape DLT dans Dagster lors du run sur Snowflake (4 min 33 s)](../../captures/Capture14.png){#fig:dlt width=100%}

## Transformations avec dbt

La couche Silver contient sept vues `stg_*` qui renomment et typent les colonnes. Par exemple, `stg_invoice_lines` joint les lignes de facture à leur en-tête pour récupérer la date et le client. La couche Gold contient les quatre dimensions et les deux tables de faits. Les dossiers `staging` et `marts` sont envoyés dans les schémas `silver` et `gold` ; il a fallu surcharger la macro `generate_schema_name`, sinon dbt crée des schémas nommés `SILVER_SILVER` et `SILVER_GOLD`.

``` {.sql #code:fct caption="Table de faits des ventes (models/marts/fct_sales.sql)"}
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

Le chiffre d'affaires HT et TTC est calculé une seule fois ici (lignes 10 et 11), donc aucune requête de l'application n'a à le recalculer. Les clés sont renommées (`product_id`, `salesperson_id`) pour avoir le même nom que dans les dimensions, ce qui simplifie les jointures que le modèle de langage doit écrire.

Les tests sont déclarés dans les fichiers YAML de documentation :

``` {.yaml #code:tests caption="Extrait des tests de fct_sales (models/marts/_marts.yml)"}
  - name: fct_sales
    columns:
      - name: order_line_id
        data_tests: [unique, not_null]
      - name: product_id
        data_tests:
          - relationships:
              arguments: {to: ref('dim_products'), field: product_id}
```

Le test `unique` sur la clé vérifie qu'aucune jointure n'a dupliqué de lignes, et `relationships` vérifie que chaque vente pointe vers un produit qui existe. Il y a dix-huit tests au total. `dbt build` exécute les 13 modèles et les tests dans l'ordre (31 nœuds).

![Lignage dbt, des sources Bronze aux tables Gold](figures/dbt_lineage.png){#fig:lineage width=100%}

## Orchestration avec Dagster

Les deux composants sont déclarés dans des fichiers `defs.yaml`. Pour dbt, il suffit d'indiquer le dossier du projet et la commande `build`. Au début, notre fichier s'appelait `defs.yml` : Dagster l'ignorait sans afficher d'erreur et l'étape dbt n'apparaissait pas. C'est `dg list defs` qui nous a permis de voir ce qui était vraiment chargé.

``` {.python #code:schedule caption="Job et planification (defs/schedules.py)"}
pipeline_complet = dg.define_asset_job(name="pipeline_complet", selection="*")

schedule_quotidien = dg.ScheduleDefinition(
    job=pipeline_complet,
    cron_schedule="0 2 * * *",
    execution_timezone="Africa/Dakar",
)
```

Le job sélectionne tous les actifs, et Dagster les lance dans l'ordre du lignage : DLT d'abord, puis dbt. Il est planifié tous les jours à 2 h, heure de Dakar. Le run complet sur Snowflake a duré 7 min 28 s, dont 4 min 33 s pour DLT et 23 s pour dbt (figure [@fig:run]).

![Run complet du job `pipeline_complet` sur Snowflake](../../captures/Capture16.png){#fig:run width=100%}

## Passage à Snowflake

Côté code, il a suffi de changer `DLT_DESTINATION` et `DBT_TARGET` et de renseigner les identifiants Snowflake dans des variables d'environnement. Nous avons créé un rôle `PFPB_ROLE` avec l'usage de la base `PROJET_FINAL_PRATIQUE_BI` et du warehouse `COMPUTE_WH` (taille XSMALL, suspendu après 60 s d'inactivité).

Le vrai problème a été les droits. Nous avions créé les schémas avec `ACCOUNTADMIN`, et DLT comme dbt échouaient avec *Insufficient privileges to operate on schema*, même après plusieurs `GRANT`. Dans Snowflake, c'est le propriétaire du schéma qui peut y créer et remplacer des tables. La solution a été de transférer la propriété des schémas à `PFPB_ROLE` (`GRANT OWNERSHIP ON SCHEMA … COPY CURRENT GRANTS`), ou de les recréer avec ce rôle.

![Schéma `GOLD` dans Snowsight, avec `PFPB_ROLE` comme propriétaire](../../captures/Capture18.png){#fig:gold width=100%}

## Application WWI Insight

L'application est en Streamlit. Elle a une page d'accueil avec quelques chiffres calculés sur la couche Gold (figure [@fig:home]), une connexion avec inscription, et un espace où l'utilisateur range ses questions dans des dossiers. Les comptes et les analyses sont stockés dans une petite base SQLite, avec des mots de passe hachés en bcrypt. Pour ne pas être déconnecté quand on recharge la page, un jeton de session valable sept jours est gardé dans l'adresse.

![Page d'accueil connectée à Snowflake](../../captures/Capture20.png){#fig:home width=90%}

### Génération du SQL

Au démarrage, l'application teste Cortex. Sur notre compte d'essai, l'appel à `SNOWFLAKE.CORTEX.COMPLETE` est refusé, elle passe donc sur Ollama avec le modèle `qwen2.5-coder:7b`, installé sur la machine. Si aucun des deux ne répond, seules les questions d'exemple restent utilisables. La consigne envoyée au modèle est volontairement courte :

``` {.python #code:prompt caption="Consigne envoyée au modèle (presentation_app/warehouse.py)"}
PROMPT = """Tu es un expert SQL {dialect}. Tu réponds aux questions sur l'entreprise
Wide World Importers à partir de ce schéma (couche GOLD) :

{schema}

Règles :
- une seule requête SELECT, uniquement sur les tables gold ci-dessus ;
- chiffre d'affaires = sum(sales_amount_excl_tax) de gold.fct_sales ;
- bénéfice = sum(line_profit) de gold.fct_invoice_lines ;
- noms de colonnes de résultat en français et en snake_case ;
- {max_rows} lignes maximum.
Réponds uniquement avec le SQL, sans explication ni balise.

Question : {question}"""
```

Le schéma n'est pas écrit à la main : il est lu dans `information_schema.columns` et réduit à une ligne par table, ce qui raccourcit la consigne pour le modèle local. Les deux règles des lignes 8 et 9 servent à ce que le modèle prenne la bonne table de faits, puisque le bénéfice ne se trouve que dans `fct_invoice_lines`.

### Contrôle des requêtes

Avant d'être exécutée, la requête passe par `clean_sql` :

``` {.python #code:clean caption="Contrôle de la requête (presentation_app/warehouse.py)"}
def clean_sql(sql: str) -> str:
    sql = re.sub(r"```(?:sql)?", "", sql, flags=re.IGNORECASE).strip().rstrip(";").strip()
    if not re.match(r"^(select|with)\b", sql, re.IGNORECASE):
        raise QueryError("Requête refusée : seules les requêtes SELECT sont autorisées.")
    if ";" in sql:
        raise QueryError("Requête refusée : une seule instruction est autorisée.")
    if FORBIDDEN.search(re.sub(r"'[^']*'", "''", sql)):
        raise QueryError("Requête refusée : elle contient une instruction d'écriture.")
    if not re.search(r"\blimit\s+\d+\s*$", sql, re.IGNORECASE):
        sql = f"{sql}\nlimit {MAX_ROWS}"
    return sql
```

On enlève d'abord les balises Markdown que le modèle ajoute parfois. La requête doit ensuite commencer par `SELECT` ou `WITH`, ne contenir qu'une instruction et aucun mot-clé d'écriture (`insert`, `drop`, `grant`…). Le contenu des chaînes est vidé avant cette recherche, pour qu'un filtre comme `'drop shipping'` ne soit pas refusé à tort. Enfin, un `LIMIT 1000` est ajouté s'il manque.

### Exemple

La figure [@fig:ollama] montre une question libre posée sur Snowflake : « Les 10 produits les plus vendus ? ». Ollama a mis 36,5 s pour écrire le SQL. L'onglet SQL (figure [@fig:sql]) montre une requête correcte : somme de `quantity` dans `fct_sales`, jointure avec `dim_products`, tri décroissant. Le premier produit (*Black and orange fragile despatch tape 48mmx75m*, 207 324 unités) est le même que celui obtenu avec une requête écrite à la main.

![Réponse à une question libre, SQL généré par Ollama](../../captures/capture22.png){#fig:ollama width=100%}

![Requête générée, onglet SQL](../../captures/Capture23.png){#fig:sql width=100%}
