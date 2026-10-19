# WWI Insight — Modern Data Platform & Text-to-SQL

Projet M2 BI (FST, UCAD) : plateforme de données en architecture Médaillon sur la base
Wide World Importers, et application Streamlit qui répond aux questions en langage naturel
grâce à Snowflake Cortex AI.

```
SQL Server (WWI) --DLT--> BRONZE --dbt--> SILVER --dbt--> GOLD --Cortex AI--> Streamlit
                 \_______________ orchestré par Dagster _______________/
```

## Installation

```bash
uv sync
source .venv/bin/activate
```

Identifiants SQL Server / Snowflake pour DLT : `.dlt/secrets.toml` (non versionné).

## Pipeline de données

```bash
export DUCKDB_PATH=$PWD/warehouse.duckdb   # mode local
dg dev                                     # http://localhost:3000 → job pipeline_complet
```

Pour Snowflake : `DLT_DESTINATION=snowflake`, `DBT_TARGET=prod`, `SF_ACCOUNT`, `SF_USER`, `SF_PASSWORD`.

## Application WWI Insight

```bash
streamlit run presentation_app/app.py
```

- **Mode local (DuckDB)** par défaut : lit `warehouse.duckdb` ; seules les questions d'exemple
  sont traduites en SQL (Cortex n'existe que sur Snowflake), le SQL peut être écrit à la main.
- **Mode Snowflake** dès que `SF_ACCOUNT` est défini : génération SQL par Cortex
  (`CORTEX_MODEL`, défaut `mistral-large2`). Variables optionnelles : `SF_ROLE`,
  `SF_WAREHOUSE`, `SF_DATABASE`.
- Comptes, dossiers et analyses : base SQLite `presentation_app/data/users.db`
  (mots de passe hachés avec bcrypt).
- Seules les requêtes `SELECT` sont exécutées, limitées à 1 000 lignes.

Les informations de la page « À propos » (nom, encadrant, année) se modifient dans
`presentation_app/settings.py` (`PROJECT`).

| Fichier | Rôle |
|---|---|
| `presentation_app/app.py` | point d'entrée et navigation |
| `presentation_app/warehouse.py` | génération Cortex, contrôle et exécution du SQL |
| `presentation_app/users_db.py` | utilisateurs, dossiers et analyses (SQLite) |
| `presentation_app/ui.py` | thème, composants, graphiques |
| `presentation_app/views/` | pages : accueil, connexion, espace d'analyse, à propos |
