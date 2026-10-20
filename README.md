# WWI Insight — Modern Data Platform & Text-to-SQL

Projet M2 BI (FST, UCAD) : plateforme de données en architecture Médaillon sur la base
Wide World Importers, et application Streamlit qui répond aux questions en langage naturel
grâce à Snowflake Cortex AI.

```
SQL Server (WWI) --DLT--> BRONZE --dbt--> SILVER --dbt--> GOLD --Cortex AI--> Streamlit
                 \_______________ orchestré par Dagster _______________/
```

Ce document reprend **toutes les commandes**, de la création du projet au lancement de
l'application. Les captures du dossier `captures/` illustrent les étapes correspondantes.

> Vous clonez simplement le dépôt ? Passez directement à [Démarrage rapide](#démarrage-rapide).

---

## 0. Prérequis

- Ubuntu (ou WSL Ubuntu sous Windows), Python 3.10 à 3.14
- [uv](https://docs.astral.sh/uv/) :
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- SQL Server avec la base **WideWorldImporters** restaurée
  (fichier `WideWorldImporters-Full.bak` des exemples officiels Microsoft, restauré avec SSMS
  ou `sqlcmd`), joignable sur le port 1433
- Un compte Snowflake (étape 6 et application en mode Cortex)

---

## 1. Créer le projet Dagster — *Captures 1 et 2*

```bash
cd ~
uvx create-dagster project projet_final_pratique_bi
# « Run uv sync? » → y
cd projet_final_pratique_bi
source .venv/bin/activate
```

---

## 2. Installer les dépendances — *Capture 3*

```bash
uv add "dlt[snowflake,duckdb,mssql]" pyodbc pymssql dagster-dlt
uv add dagster-dbt dbt-core dbt-duckdb dbt-snowflake
uv add streamlit snowflake-connector-python pandas bcrypt
```

---

## 3. Couche Bronze : ingestion DLT

### 3.1 Générer le composant DLT — *Capture 3*

```bash
dg scaffold defs dagster_dlt.DltLoadCollectionComponent mssql_ingestion \
  --source sql_database --destination snowflake
```

Cela crée `src/projet_final_pratique_bi/defs/mssql_ingestion/` (`defs.yaml`, `loads.py`).
Le fichier `loads.py` de ce dépôt définit les 10 tables chargées (Customers, Orders,
OrderLines, Invoices, InvoiceLines, StockItems, Cities, StateProvinces, Countries, People),
le chargement incrémental (`merge` sur `LastEditedWhen`) et la destination
(`DLT_DESTINATION=duckdb` ou `snowflake`).

### 3.2 Identifiants — *Captures 4 et 5*

Créer `.dlt/secrets.toml` **à la racine du projet** (dossier depuis lequel on lance `dg dev`).
Ce fichier est ignoré par git : ne jamais le commiter.

```toml
[sources.sql_database.credentials]
drivername = "mssql+pymssql"
host = "<serveur_sql>"
port = "1433"
database = "WideWorldImporters"
username = "<utilisateur>"
password = "<mot_de_passe>"

[destination.snowflake.credentials]
database = "PROJET_FINAL_PRATIQUE_BI"
username = "<utilisateur_snowflake>"
password = "<mot_de_passe_snowflake>"
host = "<identifiant_compte>"      # ex. abcdefg-xy12345
warehouse = "COMPUTE_WH"
role = "PFPB_ROLE"
```

### 3.3 Premier chargement dans DuckDB — *Captures 6 et 7*

```bash
export DUCKDB_PATH=$PWD/warehouse.duckdb       # même fichier pour DLT, dbt et l'application
DLT_DESTINATION=duckdb python src/projet_final_pratique_bi/defs/mssql_ingestion/loads.py
dg list defs                                    # les assets bronze/* apparaissent
```

Astuce : ajouter `export DUCKDB_PATH=...` dans `~/.bashrc` pour ne pas le retaper.

> Avec un fichier `.env` à la racine (chargé automatiquement par `dg dev`), écrire le chemin
> **absolu** : `DUCKDB_PATH=/home/<utilisateur>/projet_final_pratique_bi/warehouse.duckdb`.
> Un `.env` ne remplace pas `$HOME` ni `$PWD` (le projet tolère `$HOME`, pas `$PWD`).

---

## 4. Couches Silver et Gold : dbt

### 4.1 Créer le projet dbt

```bash
cd src/projet_final_pratique_bi/defs
dbt init transform --skip-profile-setup
cd transform
```

Fichiers du dépôt à reprendre dans `transform/` :

| Fichier | Rôle |
|---|---|
| `profiles.yml` | cible `dev` (DuckDB, `DUCKDB_PATH`) et `prod` (Snowflake, variables `SF_*`) |
| `dbt_project.yml` | `staging` → vues dans le schéma `silver`, `marts` → tables dans `gold` |
| `macros/generate_schema_name.sql` | schémas `silver` / `gold` exacts (sans préfixe) |
| `models/_sources.yml` | tables Bronze (noms DLT en snake_case) |
| `models/staging/*.sql` + `_staging.yml` | 7 modèles Silver + tests |
| `models/marts/*.sql` + `_marts.yml` | `fct_sales`, `fct_invoice_lines`, `dim_customers`, `dim_products`, `dim_salespeople`, `dim_date` + tests |

### 4.2 Construire et tester

```bash
dbt debug --profiles-dir .                 # vérifie la connexion
dbt build --profiles-dir .                 # modèles + tests (31 OK attendus)
dbt docs generate --profiles-dir . && dbt docs serve --profiles-dir .   # lineage, pour le rapport
cd ../../../..                             # retour à la racine du projet
```

---

## 5. Orchestration : Dagster

Fichiers du dépôt :

- `src/projet_final_pratique_bi/defs/transform/defs.yaml` : composant `dagster_dbt.DbtProjectComponent`
  (attention : l'extension doit être **`.yaml`**, un `defs.yml` est ignoré par Dagster) ;
- `src/projet_final_pratique_bi/defs/schedules.py` : job `pipeline_complet` (tous les assets)
  et planification quotidienne à 2 h (Africa/Dakar).

```bash
dg check defs          # valide la configuration
dg list defs           # bronze/*, silver/stg_*, gold/*, job et schedule
dg dev                 # http://localhost:3000
```

Dans l'interface : **Assets → Global asset lineage → Materialize all** (ou **Jobs →
pipeline_complet → Launchpad**), puis activer le schedule dans **Automation**.

> DuckDB n'accepte qu'un seul écrivain : fermer DBeaver / l'application pendant un run.

---

## 6. Passage à Snowflake

### 6.1 Préparer le compte (worksheet Snowsight)

Les schémas doivent **appartenir** à `PFPB_ROLE` : créés par ACCOUNTADMIN, DLT et dbt
échouent avec « Insufficient privileges… must have CREATE TABLE granted on SCHEMA ».
ACCOUNTADMIN donne donc les droits, puis `PFPB_ROLE` crée lui-même ses schémas.

```sql
-- 1) Droits (ACCOUNTADMIN)
USE ROLE ACCOUNTADMIN;
CREATE ROLE IF NOT EXISTS PFPB_ROLE;
CREATE WAREHOUSE IF NOT EXISTS COMPUTE_WH WAREHOUSE_SIZE = XSMALL AUTO_SUSPEND = 60 AUTO_RESUME = TRUE;
CREATE DATABASE IF NOT EXISTS PROJET_FINAL_PRATIQUE_BI;
GRANT USAGE ON DATABASE PROJET_FINAL_PRATIQUE_BI TO ROLE PFPB_ROLE;
GRANT CREATE SCHEMA ON DATABASE PROJET_FINAL_PRATIQUE_BI TO ROLE PFPB_ROLE;
GRANT USAGE ON WAREHOUSE COMPUTE_WH TO ROLE PFPB_ROLE;
GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE PFPB_ROLE;
GRANT ROLE PFPB_ROLE TO USER <utilisateur_snowflake>;

-- 2) Schémas créés par PFPB_ROLE, qui en devient propriétaire
USE ROLE PFPB_ROLE;
USE WAREHOUSE COMPUTE_WH;
CREATE SCHEMA IF NOT EXISTS PROJET_FINAL_PRATIQUE_BI.BRONZE;
CREATE SCHEMA IF NOT EXISTS PROJET_FINAL_PRATIQUE_BI.SILVER;
CREATE SCHEMA IF NOT EXISTS PROJET_FINAL_PRATIQUE_BI.GOLD;
SHOW SCHEMAS IN DATABASE PROJET_FINAL_PRATIQUE_BI;   -- owner = PFPB_ROLE
```

Schémas déjà créés par ACCOUNTADMIN : les supprimer (`DROP SCHEMA …`) puis relancer l'étape 2,
ou transférer la propriété :
`GRANT OWNERSHIP ON SCHEMA PROJET_FINAL_PRATIQUE_BI.BRONZE TO ROLE PFPB_ROLE COPY CURRENT GRANTS;`

### 6.2 Lancer le pipeline sur Snowflake

```bash
export DLT_DESTINATION=snowflake
export DBT_TARGET=prod
export SF_ACCOUNT=<identifiant_compte> SF_USER=<utilisateur> SF_PASSWORD='<mot_de_passe>'
dg dev                 # Materialize all → schémas BRONZE, SILVER, GOLD remplis dans Snowflake
```

---

## 7. Application WWI Insight (Streamlit)

### 7.1 Modèle d'IA qui écrit le SQL

L'application choisit automatiquement (`SQL_GENERATOR=auto`) :

1. **Snowflake Cortex** (`CORTEX_MODEL`, défaut `mistral-large2`) s'il répond ;
2. sinon **Ollama**, un modèle local et gratuit (`OLLAMA_MODEL`, défaut `qwen2.5-coder:7b`) ;
3. sinon les 4 questions d'exemple seulement (et le SQL écrit à la main).

> `SNOWFLAKE.CORTEX.COMPLETE` n'est **pas disponible sur les comptes d'essai** Snowflake
> (« AI function COMPLETE is not available for trial accounts ») : Ollama prend alors le relais.
> Le SQL généré reste exécuté sur la couche Gold de Snowflake.

Installer Ollama (une fois, dans WSL/Ubuntu) :

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5-coder:7b        # ~4,7 Go ; machine modeste : qwen2.5-coder:3b + OLLAMA_MODEL=qwen2.5-coder:3b
ollama serve                         # si le service ne tourne pas déjà (laisser ce terminal ouvert)
```

### 7.2 Lancer l'application

```bash
# Mode local : lit warehouse.duckdb
export DUCKDB_PATH=$PWD/warehouse.duckdb
streamlit run presentation_app/app.py           # http://localhost:8501

# Mode Snowflake : la couche Gold est lue dans Snowflake
export SF_ACCOUNT=<identifiant_compte> SF_USER=<utilisateur> SF_PASSWORD='<mot_de_passe>'
streamlit run presentation_app/app.py
```

Le badge en haut de l'espace d'analyse indique la source et le modèle utilisés, par exemple
`SNOWFLAKE · GOLD · ollama/qwen2.5-coder:7b`.

Parcours : accueil → **Se connecter** → onglet **Inscription** → espace d'analyse →
poser une question (ou cliquer un exemple) → tableau / graphique / export CSV.

- Comptes, dossiers et analyses : base SQLite `presentation_app/data/users.db`
  (mots de passe hachés avec bcrypt, fichier ignoré par git).
- Seules les requêtes `SELECT` sont exécutées, limitées à 1 000 lignes.
- Nom, encadrant et année de la page « À propos » : `PROJECT` dans `presentation_app/settings.py`.
- Variables optionnelles : `SF_ROLE`, `SF_WAREHOUSE`, `SF_DATABASE`, `APP_BACKEND`
  (`duckdb` ou `snowflake`, pour forcer le mode), `SQL_GENERATOR` (`auto`, `cortex`, `ollama`,
  `none`), `OLLAMA_URL`, `OLLAMA_MODEL`, `APP_USERS_DB`.

| Fichier | Rôle |
|---|---|
| `presentation_app/app.py` | point d'entrée |
| `presentation_app/session.py` | navigation et session persistante (jeton valable 7 jours, conservé dans l'URL) |
| `presentation_app/warehouse.py` | génération du SQL (Cortex ou Ollama), contrôle et exécution |
| `presentation_app/users_db.py` | utilisateurs, dossiers et analyses (SQLite) |
| `presentation_app/ui.py` | thème, composants, graphiques |
| `presentation_app/views/` | pages : accueil, connexion, espace d'analyse, à propos (+ barre de navigation commune) |

---

## Démarrage rapide

Après un `git clone` du dépôt (SQL Server et `.dlt/secrets.toml` prêts) :

```bash
cd projet_final_pratique_bi
uv sync && source .venv/bin/activate
export DUCKDB_PATH=$PWD/warehouse.duckdb

DLT_DESTINATION=duckdb python src/projet_final_pratique_bi/defs/mssql_ingestion/loads.py   # Bronze
(cd src/projet_final_pratique_bi/defs/transform && dbt build --profiles-dir .)              # Silver + Gold
streamlit run presentation_app/app.py                                                         # application
```

Ou, pour tout orchestrer : `dg dev` puis **Materialize all**.
