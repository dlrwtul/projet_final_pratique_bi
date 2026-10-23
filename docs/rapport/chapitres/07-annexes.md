# Annexes {.unnumbered}

## A. Commandes principales {.unnumbered}

Les commandes suivantes reconstruisent la plateforme à partir du dépôt. Elles supposent SQL Server accessible et le fichier `.dlt/secrets.toml` renseigné.

```bash
# Installation
uv sync && source .venv/bin/activate

# Développement local (DuckDB)
export DUCKDB_PATH=$PWD/warehouse.duckdb
dg check defs                  # valide la configuration Dagster
dg list defs                   # liste les actifs, le job et la planification
dg dev                         # interface Dagster : http://localhost:3000

# Production (Snowflake)
export DLT_DESTINATION=snowflake DBT_TARGET=prod
export SF_ACCOUNT=<compte> SF_USER=<utilisateur> SF_PASSWORD='<mot_de_passe>'
dg dev                         # puis « Materialize all »

# Modèle local pour la génération du SQL
ollama pull qwen2.5-coder:7b

# Application
streamlit run presentation_app/app.py       # http://localhost:8501
```

## B. Variables d'environnement {.unnumbered}

Variable           Valeur par défaut                Rôle
------------------ -------------------------------- ---------------------------------------------
`DLT_DESTINATION`  `duckdb`                         destination de l'ingestion
`DBT_TARGET`       `dev`                            cible dbt (`dev` ou `prod`)
`DUCKDB_PATH`      `warehouse.duckdb`               fichier DuckDB local
`SF_ACCOUNT`       aucune                           identifiant du compte Snowflake
`SF_USER`          aucune                           utilisateur Snowflake
`SF_PASSWORD`      aucune                           mot de passe Snowflake
`SF_ROLE`          `PFPB_ROLE`                      rôle utilisé par l'application
`SF_WAREHOUSE`     `COMPUTE_WH`                     warehouse Snowflake
`SQL_GENERATOR`    `auto`                           `auto`, `cortex`, `ollama` ou `none`
`CORTEX_MODEL`     `mistral-large2`                 modèle Cortex
`OLLAMA_MODEL`     `qwen2.5-coder:7b`               modèle Ollama
`OLLAMA_URL`       `http://localhost:11434`         adresse du serveur Ollama


## C. Exécution d'une question dans l'application {.unnumbered}

La fonction `_ask` du fichier `presentation_app/views/workspace.py` enchaîne les étapes décrites au chapitre 3.

```python
def _ask(user: dict, folder_id: int, question: str, sql: str | None = None) -> None:
    st.html(f'<div class="wwi-question"><div>{html.escape(question)}</div></div>')
    start = time.perf_counter()
    engine = "manuel" if sql else None
    try:
        with st.spinner("Génération du SQL et exécution sur la couche Gold…"):
            if not sql:
                sql, engine = warehouse.generate_sql(question)
            sql = warehouse.clean_sql(sql)
            df = warehouse.run_sql(sql)
    except warehouse.QueryError as exc:
        st.session_state.last_error = (question, str(exc), sql)
        st.rerun()
    st.session_state.pop("last_error", None)
    users_db.add_analysis(user["id"], folder_id, question, sql,
                          df.to_json(orient="split", date_format="iso", index=False), len(df),
                          engine, int((time.perf_counter() - start) * 1000))
    st.rerun()
```

Une requête saisie directement par l'utilisateur est marquée `manuel` et passe par le même contrôle `clean_sql` que le SQL généré. Toute erreur, qu'elle vienne du modèle, du filtre ou de la base, est convertie en `QueryError` et affichée sous la question. En cas de succès, le résultat est enregistré avec le moteur utilisé et la durée totale en millisecondes.

## D. Lancement de l'application {.unnumbered}

La commande `streamlit run presentation_app/app.py` démarre l'application sur le port 8501.

![](../../captures/Capture19.png){width=80%}
