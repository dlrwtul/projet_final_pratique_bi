# Mise en œuvre de la plateforme

Ce chapitre suit l'ordre de la chaîne : initialisation du projet, ingestion, transformations, orchestration, passage à Snowflake, puis application. Les extraits de code sont tirés du dépôt ; les numéros de ligne cités renvoient aux extraits tels qu'ils sont reproduits.

## Initialisation du projet

Le projet a été créé avec `create-dagster`, l'outil d'initialisation de Dagster, qui génère un projet Python géré par `uv` (figure [@fig:init]). Les dépendances ont ensuite été ajoutées avec `uv add` : `dlt[snowflake,duckdb,mssql]`, `pyodbc` et `dagster-dlt` pour l'ingestion, `dagster-dbt`, `dbt-duckdb` et `dbt-snowflake` pour les transformations, `streamlit` et `bcrypt` pour l'application.

![Création du projet avec `create-dagster`](../../captures/Capture2.png){#fig:init width=95%}

Dagster organise un projet en *composants*. Chaque dossier placé sous `defs/` et contenant un fichier `defs.yaml` est chargé automatiquement au démarrage. Le composant d'ingestion a été généré par la commande `dg scaffold defs dagster_dlt.DltLoadCollectionComponent mssql_ingestion`, avec SQL Server comme source et Snowflake comme destination (figure [@fig:scaffold]), puis le projet dbt a été placé dans le dossier `defs/transform`.

![Ajout des dépendances et génération du composant DLT](../../captures/Capture3.png){#fig:scaffold width=95%}

La figure [@fig:arbo] montre l'arborescence obtenue. On y retrouve les deux composants (`mssql_ingestion` et `transform`), le fichier `schedules.py` qui définit la planification, et le dossier `presentation_app` qui contient l'application.

![Arborescence du projet](../../captures/Capture4.png){#fig:arbo width=34%}

## Ingestion de la couche Bronze avec DLT

La couche Bronze reçoit les données de SQL Server sans transformation métier. Chacune des dix tables retenues au chapitre précédent est déclarée comme une ressource de la source DLT `wwi`, dans le fichier `defs/mssql_ingestion/loads.py`.

``` {.python #code:dlt-source caption="Déclaration de la source DLT (defs/mssql_ingestion/loads.py)"}
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
    # ... huit autres tables, déclarées de la même façon
```

Deux modes de chargement coexistent. Les tables de référence, peu volumineuses, sont rechargées entièrement à chaque exécution (`write_disposition="replace"`, ligne 5). Les tables de faits sont chargées de façon incrémentale : DLT mémorise la plus grande valeur de `LastEditedWhen` déjà lue et, à l'exécution suivante, ne récupère que les lignes modifiées depuis (ligne 11). Le mode `merge`, associé à la clé primaire `OrderID` (ligne 10), met à jour une commande déjà chargée au lieu de la dupliquer.

Les colonnes de type `geography` de SQL Server (`DeliveryLocation`, `Location`, `Border`) sont exclues (ligne 6), de même que les photos et les mots de passe chiffrés de la table `People`. Avant cette exclusion, chaque chargement affichait un avertissement de DLT, qui ne sait pas convertir ce type (figure [@fig:geo]).

![Avertissements de DLT sur les colonnes `geography` lors des premiers chargements](../../captures/Capture6.png){#fig:geo width=90%}

Le code d'accès à SQL Server ne contient aucun mot de passe. DLT lit la chaîne de connexion dans le fichier `.dlt/secrets.toml`, exclu du dépôt Git (figure [@fig:secrets]).

![Fichier `.dlt/secrets.toml` (valeurs masquées)](../../captures/Capture5.png){#fig:secrets width=85%}

La fin du fichier choisit la destination à partir de la variable `DLT_DESTINATION`.

``` {.python #code:dlt-dest caption="Choix de la destination et définition du pipeline (loads.py)"}
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
```

Le paramètre `dataset_name` (ligne 11) donne le nom du schéma cible : `bronze` dans DuckDB, `BRONZE` dans Snowflake. La ligne 3 corrige un problème rencontré pendant le développement : Dagster lit le fichier `.env` sans interpréter les variables du shell, si bien que le chemin `$HOME/…` arrivait tel quel dans le code et DuckDB créait un dossier nommé littéralement `$HOME`.

DLT normalise les identifiants : `OrderLines` devient `order_lines` et `CustomerID` devient `customer_id`. Nos premiers modèles dbt, écrits avec les noms de SQL Server, échouaient pour cette raison. Le tableau [@tab:bronze] donne les volumes chargés dans Snowflake, relevés après exécution.

::: {#tab:bronze}
Table                      Lignes  Mode de chargement
---------------------- ----------  ----------------------
`order_lines`             231 412  incrémental (`merge`)
`invoice_lines`           228 265  incrémental (`merge`)
`orders`                   73 595  incrémental (`merge`)
`invoices`                 70 510  incrémental (`merge`)
`cities`                   37 940  complet (`replace`)
`people`                    1 111  complet (`replace`)
`customers`                   663  complet (`replace`)
`stock_items`                 227  complet (`replace`)
`countries`                   190  complet (`replace`)
`state_provinces`              53  complet (`replace`)

: Volumes chargés dans le schéma `BRONZE` de Snowflake
:::

## Transformations Silver et Gold avec dbt

### Déclaration des sources

Le projet dbt commence par déclarer les tables Bronze comme des *sources*. Chaque source porte un nom logique, repris de SQL Server, et le nom physique créé par DLT (`identifier`).

``` {.yaml #code:sources caption="Sources Bronze déclarées dans dbt (models/_sources.yml)"}
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
```

Ce double nommage a une seconde utilité. Dagster relie un modèle dbt à l'actif DLT qui l'alimente en comparant le nom de la source à celui de la ressource DLT, qui reprend le nom de la table SQL Server. Avec `name: OrderLines` et `identifier: order_lines` (lignes 11 et 12), le lien est établi automatiquement et le lignage passe de DLT à dbt sans configuration supplémentaire.

### Placement des modèles dans les schémas

Les modèles sont rangés par couche dans `dbt_project.yml` : le dossier `staging` produit des vues dans le schéma `silver`, le dossier `marts` des tables dans le schéma `gold`. Par défaut, dbt préfixe ce nom par le schéma de la cible et aurait créé `SILVER_SILVER` et `SILVER_GOLD`. La macro du code [@code:schema] remplace ce comportement.

``` {.sql #code:schema caption="Surcharge du nommage des schémas (macros/generate_schema_name.sql)"}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
```

Quand un modèle déclare un schéma, ce nom est utilisé tel quel (ligne 5) ; sinon le modèle va dans le schéma de la cible (ligne 3).

### Couche Silver

La couche Silver compte sept vues `stg_*`, une par table utile. Elles renomment et typent les colonnes, et effectuent les jointures purement techniques. Ainsi, la date de facturation et le client sont portés par l'en-tête de facture, alors que le bénéfice est porté par la ligne ; la vue `stg_invoice_lines` rassemble les deux.

``` {.sql #code:stg caption="Vue Silver des lignes de facture (models/staging/stg_invoice_lines.sql)"}
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
```

La fonction `source()` (lignes 2 et 5) désigne une table Bronze par son nom logique ; dbt en déduit l'ordre d'exécution et le lignage. La conversion de la ligne 14 ramène la date de facturation au type `DATE`, qui se joint directement à la dimension calendrier.

### Couche Gold

La couche Gold contient les quatre dimensions et les deux tables de faits décrites au chapitre 2. Le code [@code:fct] montre la table `fct_sales`, qui porte la définition du chiffre d'affaires.

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

Le grain est la ligne de commande : la jointure de la ligne 13 rattache chaque ligne à sa commande sans la dupliquer, puisqu'une ligne n'appartient qu'à une commande. Les lignes 6 et 7 renomment les clés pour qu'elles portent le même nom que dans les dimensions, ce qui simplifie les jointures écrites par le modèle de langage. Les montants hors taxes et toutes taxes comprises sont calculés une fois pour toutes (lignes 10 et 11) : aucune requête n'a à refaire ce calcul. La fonction `ref()` désigne un autre modèle dbt, ici deux vues Silver.

La dimension `dim_date` est générée par la macro `dbt.date_spine`, qui produit un jour par ligne du 1^er^ janvier 2013 au 31 décembre 2016, soit 1 461 lignes, avec l'année, le trimestre, le mois et le jour.

### Tests de qualité

Les tests sont déclarés dans les fichiers YAML qui documentent les modèles. Le code [@code:tests] en montre une partie pour la couche Gold.

``` {.yaml #code:tests caption="Documentation et tests de fct_sales (models/marts/_marts.yml)"}
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
```

Le test de la ligne 6 vérifie le grain : si une jointure dupliquait des lignes de commande, `unique` échouerait. Les tests `relationships` (lignes 11 et 15) vérifient que chaque vente renvoie à un produit et à un client existants ; une vente orpheline disparaîtrait sinon silencieusement des analyses qui joignent les dimensions. Le projet compte dix-huit tests au total, répartis entre les couches Silver et Gold. La commande `dbt build` exécute les treize modèles et ces tests dans l'ordre du graphe, soit 31 nœuds ; un modèle n'est construit que si les tests des modèles dont il dépend ont réussi.

La figure [@fig:dbt-lineage] présente le graphe de dépendances généré par dbt.

![Lignage des modèles dbt, des sources Bronze aux tables Gold](figures/dbt_lineage.png){#fig:dbt-lineage width=100%}

## Orchestration avec Dagster

### Déclaration des composants

Les deux composants sont déclarés en YAML ; aucun code Python n'est nécessaire pour les charger.

``` {.yaml #code:defs caption="Déclaration des composants DLT et dbt (fichiers defs.yaml)"}
# defs/mssql_ingestion/defs.yaml
type: dagster_dlt.DltLoadCollectionComponent
attributes:
  loads:
    - source: .loads.mssql_source
      pipeline: .loads.mssql_pipeline

# defs/transform/defs.yaml
type: dagster_dbt.DbtProjectComponent
attributes:
  project:
    project_dir: "{{ context.project_root }}/src/projet_final_pratique_bi/defs/transform"
    profiles_dir: "{{ context.project_root }}/src/projet_final_pratique_bi/defs/transform"
  cli_args:
    - build
```

Le composant DLT pointe vers la source et le pipeline définis dans `loads.py` (lignes 5 et 6) ; chaque ressource de la source devient un actif Dagster. Le composant dbt lit le projet et transforme chaque modèle, source et test en actif ou en contrôle (*asset check*). L'argument `build` (ligne 15) fait exécuter les tests en même temps que les modèles.

Une erreur nous a coûté du temps à cette étape : le fichier s'appelait d'abord `defs.yml`. Dagster n'accepte que l'extension `.yaml` et ignore l'autre sans message d'erreur ; l'étape dbt n'apparaissait donc pas. La commande `dg list defs` permet de vérifier ce qui est réellement chargé (figure [@fig:dglist]).

![Actifs et définitions chargés, vérifiés avec `dg list defs`](../../captures/Capture7.png){#fig:dglist width=80%}

### Planification

``` {.python #code:schedule caption="Job complet et planification quotidienne (defs/schedules.py)"}
import dagster as dg

pipeline_complet = dg.define_asset_job(name="pipeline_complet", selection="*")

schedule_quotidien = dg.ScheduleDefinition(
    job=pipeline_complet,
    cron_schedule="0 2 * * *",
    execution_timezone="Africa/Dakar",
)
```

Le job `pipeline_complet` sélectionne tous les actifs (ligne 3) ; Dagster les exécute dans l'ordre du lignage, l'ingestion avant les transformations. La planification le lance chaque jour à 2 h, heure de Dakar (lignes 7 et 8), un horaire où personne n'interroge l'entrepôt.

### Exécution

L'interface web de Dagster, lancée avec `dg dev`, affiche le graphe des actifs (figure [@fig:dagster-lineage]). On y lit la chaîne complète : les dix actifs DLT de la couche Bronze, les vues Silver, puis les tables Gold.

![Lignage des actifs dans Dagster, de l'ingestion DLT aux tables Gold](figures/dagster_lineage.png){#fig:dagster-lineage width=100%}

Une exécution du job se suit étape par étape. Sur Snowflake, l'ingestion des dix tables a duré 4 min 33 s (figure [@fig:run-dlt]) et l'étape dbt 23,28 s, contrôles compris (figure [@fig:run-dbt]). L'exécution complète a duré 7 min 28 s (figure [@fig:run-ok]) ; la différence correspond au démarrage des processus et à la reprise du warehouse Snowflake.

![Étape d'ingestion DLT terminée](../../captures/Capture14.png){#fig:run-dlt width=100%}

![Étape dbt terminée, avec les contrôles de qualité](../../captures/Capture15.png){#fig:run-dbt width=100%}

![Exécution complète du job `pipeline_complet`](../../captures/Capture16.png){#fig:run-ok width=100%}

## Passage à Snowflake

### Droits et propriété des schémas

Le passage à Snowflake n'a demandé aucune modification du code, seulement la préparation du compte. Nous avons créé un rôle dédié, `PFPB_ROLE`, plutôt que d'utiliser `ACCOUNTADMIN`.

``` {.sql #code:grants caption="Préparation du compte Snowflake (feuille de calcul Snowsight)"}
USE ROLE ACCOUNTADMIN;
CREATE ROLE IF NOT EXISTS PFPB_ROLE;
CREATE WAREHOUSE IF NOT EXISTS COMPUTE_WH WAREHOUSE_SIZE = XSMALL AUTO_SUSPEND = 60 AUTO_RESUME = TRUE;
CREATE DATABASE IF NOT EXISTS PROJET_FINAL_PRATIQUE_BI;
GRANT USAGE ON DATABASE PROJET_FINAL_PRATIQUE_BI TO ROLE PFPB_ROLE;
GRANT CREATE SCHEMA ON DATABASE PROJET_FINAL_PRATIQUE_BI TO ROLE PFPB_ROLE;
GRANT USAGE ON WAREHOUSE COMPUTE_WH TO ROLE PFPB_ROLE;
GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE PFPB_ROLE;
GRANT ROLE PFPB_ROLE TO USER <utilisateur_snowflake>;

USE ROLE PFPB_ROLE;
CREATE SCHEMA IF NOT EXISTS PROJET_FINAL_PRATIQUE_BI.BRONZE;
CREATE SCHEMA IF NOT EXISTS PROJET_FINAL_PRATIQUE_BI.SILVER;
CREATE SCHEMA IF NOT EXISTS PROJET_FINAL_PRATIQUE_BI.GOLD;
```

Le warehouse est le plus petit proposé (`XSMALL`) et se suspend après soixante secondes d'inactivité (ligne 3) : il ne consomme de crédits que pendant les exécutions. La ligne 8 donne au rôle l'accès aux fonctions Cortex.

L'ordre des deux blocs compte. Nous avions d'abord créé les schémas avec `ACCOUNTADMIN` : ils appartenaient alors à ce rôle, et DLT comme dbt échouaient avec l'erreur *Insufficient privileges to operate on schema*, même après plusieurs `GRANT`. Dans Snowflake, créer et remplacer des tables dans un schéma relève du propriétaire. Les schémas sont donc créés par `PFPB_ROLE` lui-même (lignes 11 à 14) ; pour des schémas existants, `GRANT OWNERSHIP ON SCHEMA … TO ROLE PFPB_ROLE COPY CURRENT GRANTS` produit le même effet. La figure [@fig:sf-gold] montre le schéma `GOLD` après exécution, avec `PFPB_ROLE` comme propriétaire.

![Tables du schéma `GOLD` dans Snowsight, propriété de `PFPB_ROLE`](../../captures/Capture18.png){#fig:sf-gold width=100%}

### Profil dbt

Le profil dbt décrit les deux cibles ; la variable `DBT_TARGET` choisit entre elles.

``` {.yaml #code:profile caption="Profil dbt à deux cibles (defs/transform/profiles.yml)"}
transform:
  target: "{{ env_var('DBT_TARGET', 'dev') }}"
  outputs:
    dev:
      type: duckdb
      path: "{{ env_var('DUCKDB_PATH') | replace('$HOME', env_var('HOME')) }}"
      schema: main
      threads: 4
    prod:
      type: snowflake
      account: "{{ env_var('SF_ACCOUNT') }}"
      user: "{{ env_var('SF_USER') }}"
      password: "{{ env_var('SF_PASSWORD') }}"
      role: PFPB_ROLE
      warehouse: "{{ env_var('SF_WAREHOUSE', 'COMPUTE_WH') }}"
      database: PROJET_FINAL_PRATIQUE_BI
      schema: SILVER
      threads: 4
```

Les identifiants sont lus dans l'environnement (lignes 11 à 13) et n'apparaissent jamais dans le dépôt. Le filtre `replace` de la ligne 6 corrige, côté dbt, le même problème de `$HOME` que dans `loads.py`. La commande `dbt debug --target prod` a confirmé la connexion avant la première exécution (figure [@fig:dbt-debug]).

![Vérification de la connexion à Snowflake avec `dbt debug`](../../captures/Capture8.png){#fig:dbt-debug width=100%}

Après l'exécution, une requête sur les vues `INFORMATION_SCHEMA` a permis de comparer les volumes des trois couches (figure [@fig:sf-counts]). La figure [@fig:sf-preview] montre un aperçu de `FCT_SALES` dans Snowsight ; la description de la table a été proposée par la fonction de documentation automatique de Snowflake.

![Nombre de lignes par table dans les trois schémas](../../captures/Capture17.png){#fig:sf-counts width=100%}

![Aperçu de la table `FCT_SALES` dans Snowsight](figures/snowsight_fct_sales.png){#fig:sf-preview width=100%}

## Application Text-to-SQL WWI Insight

### Organisation du code

L'application est écrite avec Streamlit et répartie en modules courts :

- `settings.py` lit la configuration dans les variables d'environnement ;
- `warehouse.py` génère, contrôle et exécute le SQL ;
- `users_db.py` gère les comptes, les sessions, les dossiers et les analyses dans une base SQLite, séparée de l'entrepôt ;
- `session.py` gère la navigation et la session persistante ;
- `views/` contient une page par fichier : accueil, connexion, espace d'analyse, à propos.

Elle fonctionne sur Snowflake comme sur DuckDB : si les identifiants Snowflake sont présents, elle se connecte au schéma `GOLD` avec le rôle `PFPB_ROLE` ; sinon, elle ouvre le fichier DuckDB local en lecture seule. La page d'accueil affiche quelques chiffres clés calculés directement sur la couche Gold (figure [@fig:app-home]).

![Page d'accueil connectée à Snowflake](../../captures/Capture20.png){#fig:app-home width=100%}

### Consigne transmise au modèle

La qualité du SQL produit dépend surtout de la consigne. Celle de l'application est courte.

``` {.python #code:prompt caption="Consigne envoyée au modèle de langage (presentation_app/warehouse.py)"}
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

Le dialecte (ligne 1) vaut `Snowflake` ou `DuckDB`, les deux n'ayant pas exactement les mêmes fonctions de date. Le schéma (ligne 4) n'est pas écrit à la main : il est lu dans `information_schema.columns` au démarrage, puis réduit à une ligne par table avec des types simplifiés (`texte`, `nombre`, `date`). Une consigne plus courte est traitée plus vite par un modèle local. Les lignes 8 et 9 fixent les deux définitions métier. Sans elles, le modèle doit deviner quelle table de faits utiliser : il pourrait calculer le chiffre d'affaires à partir des factures, ou chercher un bénéfice dans `fct_sales`, qui n'en contient pas.

### Choix du moteur de génération

Le compte d'essai Snowflake refuse l'appel à `SNOWFLAKE.CORTEX.COMPLETE`. Plutôt que de lier l'application à un seul moteur, nous la faisons choisir au démarrage.

``` {.python #code:generator caption="Sélection du moteur de génération (warehouse.py)"}
@st.cache_data(ttl=600, show_spinner=False)
def generator() -> str | None:
    """Moteur de génération utilisé : "cortex", "ollama" ou None (exemples seulement)."""
    if SQL_GENERATOR in ("cortex", "ollama"):
        return SQL_GENERATOR
    if SQL_GENERATOR == "none":
        return None
    if _cortex_available():
        return "cortex"
    if _ollama_available():
        # Préchargement du modèle en arrière-plan : la première question n'attend pas son chargement.
        threading.Thread(target=_warm_up, daemon=True).start()
        return "ollama"
    return None
```

La variable `SQL_GENERATOR` permet d'imposer un moteur (lignes 4 à 7). Par défaut, l'application tente un appel minimal à Cortex (ligne 8) ; en cas d'échec, elle vérifie qu'un serveur Ollama tourne sur le poste et qu'il dispose du modèle `qwen2.5-coder:7b` (ligne 10). Sans aucun moteur, seules les questions d'exemple restent disponibles, avec leur SQL écrit à l'avance. Le résultat est gardé en cache dix minutes (ligne 1), pour ne pas refaire ces vérifications à chaque question. La ligne 12 lance une première requête vide en arrière-plan : Ollama charge alors le modèle en mémoire avant que l'utilisateur pose sa première question.

Le SQL généré est lui aussi mis en cache, par question. Une question déjà posée obtient sa réponse en environ 0,3 s, contre une trentaine de secondes pour une génération par Ollama sur le processeur de notre machine.

### Contrôle des requêtes

Une requête produite par un modèle de langage ne peut pas être exécutée telle quelle : le modèle peut ajouter du texte autour du SQL, produire plusieurs instructions ou, sur une question mal formulée, proposer une modification des données. Chaque requête passe donc par la fonction `clean_sql`.

``` {.python #code:clean caption="Contrôle d'une requête avant exécution (warehouse.py)"}
FORBIDDEN = re.compile(
    r"\b(insert|update|delete|merge|drop|alter|create|truncate|grant|revoke|"
    r"copy|put|call|execute|attach|detach|install|pragma)\b",
    re.IGNORECASE,
)

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

La ligne 8 retire les balises Markdown et le point-virgule final. La requête doit ensuite commencer par `SELECT` ou `WITH` (ligne 9), et une seconde instruction est rejetée (ligne 11). Les mots-clés d'écriture sont recherchés après avoir vidé les chaînes de caractères (ligne 13) : une condition comme `WHERE description = 'drop shipping'` reste acceptée. Enfin, une clause `LIMIT` est ajoutée si elle manque (lignes 15 et 16), ce qui borne le résultat à mille lignes. La figure [@fig:refus] montre le refus d'une requête d'écriture.

![Requête d'écriture refusée par l'application](figures/app_requete_refusee.png){#fig:refus width=80%}

Ce filtre ne remplace pas les droits de la base. En production, l'application devrait se connecter avec un rôle limité à la lecture du schéma `GOLD` ; nous y revenons dans les limites du chapitre 4.

### Sessions et dossiers

Streamlit perd son état à chaque rechargement de la page. Pour qu'un utilisateur ne soit pas déconnecté en actualisant son navigateur, l'application crée à la connexion un jeton aléatoire, enregistré dans SQLite avec une date d'expiration, et le place dans l'adresse de la page.

``` {.python #code:session caption="Création et restauration d'une session (users_db.py et session.py)"}
SESSION_DAYS = 7

def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    expires = (datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)).isoformat(timespec="seconds")
    with _connect() as con:
        con.execute("delete from sessions where expires_at < ?", (_now(),))
        con.execute("insert into sessions (token, user_id, expires_at) values (?, ?, ?)",
                    (token, user_id, expires))
    return token

def restore() -> None:
    if "user" not in st.session_state and (token := st.query_params.get("s")):
        user = users_db.session_user(token)
        if user:
            st.session_state.user, st.session_state.token = user, token
        else:
            del st.query_params["s"]
```

Le jeton fait 32 octets aléatoires (ligne 4) et expire au bout de sept jours (lignes 1 et 5) ; les sessions expirées sont purgées à chaque nouvelle connexion (ligne 7). Au chargement de la page, `restore` relit le jeton dans le paramètre `s` de l'adresse et retrouve l'utilisateur (lignes 13 et 14). Un jeton inconnu ou expiré est retiré de l'adresse (ligne 18). La déconnexion supprime la ligne de la table `sessions`. Les mots de passe sont stockés sous forme de hachés `bcrypt`.

Chaque utilisateur range ses analyses dans des dossiers. Un dossier vide propose les questions d'exemple, regroupées par thème (figure [@fig:app-empty]). Chaque analyse enregistrée conserve la question, le SQL exécuté, le résultat, le moteur utilisé et la durée de traitement.

![Dossier vide et questions d'exemple](figures/app_dossier_vide.png){#fig:app-empty width=95%}

### Une question traitée de bout en bout

La figure [@fig:app-ollama] montre une question libre posée sur Snowflake, sans correspondance avec les exemples : « Les 10 produits les plus vendus ? ». Le SQL a été généré par Ollama en 36,5 s. L'application choisit le type de graphique d'après les colonnes du résultat, ici un diagramme en barres horizontales, et affiche une courte phrase de synthèse. L'onglet SQL (figure [@fig:app-sql]) permet de vérifier la requête : elle somme la colonne `quantity` de `fct_sales`, joint `dim_products` sur la bonne clé et trie par quantité décroissante. Le premier produit, *Black and orange fragile despatch tape 48mmx75m*, avec 207 324 unités, correspond au résultat d'une requête écrite à la main.

![Réponse à une question libre, SQL généré par Ollama](../../captures/capture22.png){#fig:app-ollama width=100%}

![Requête générée, affichée dans l'onglet SQL](../../captures/Capture23.png){#fig:app-sql width=100%}

La page « À propos » (figure [@fig:app-about]) rappelle le cadre du projet et l'architecture.

![Page « À propos »](../../captures/Capture21.png){#fig:app-about width=100%}
