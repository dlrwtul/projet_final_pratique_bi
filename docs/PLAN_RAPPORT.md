# Plan du rapport de projet

**Titre** : Conception d'une Modern Data Platform avec architecture Médaillon et développement d'une application Text-to-SQL basée sur l'IA
**Formation** : M2 BI — FST / Dép. Maths-Info, UCAD — Encadrant : Dr. Jean Gane SARR

Volume indicatif : 20 à 35 pages hors annexes. Chaque section indique quoi écrire et quelles captures mettre.

---

## Page de garde, remerciements, résumé (FR + abstract EN), sommaire, liste des figures, sigles

Sigles : BI, MDP, OLTP, ELT, DLT, dbt, SQL, LLM, Text-to-SQL, WWI.

## Introduction générale (1-2 p.)
- Contexte : volume de données, besoin de décision, IA générative et langage naturel.
- Problématique (reprendre la consigne en vos mots).
- Objectifs (général + spécifiques).
- Annonce du plan.

## Chapitre 1 — Cadre conceptuel et état de l'art (4-6 p.)
1. Du data warehouse classique à la Modern Data Platform (ETL vs ELT, cloud).
2. Architecture Médaillon : Bronze / Silver / Gold, intérêt de chaque couche.
3. Modélisation dimensionnelle (Kimball) : faits, dimensions, schéma en étoile.
4. Text-to-SQL et LLM : principe, limites (hallucinations, sécurité), approches (prompt + schéma, couche sémantique).
5. Présentation des outils et justification des choix : SQL Server, DLT, DuckDB, Snowflake, dbt, Dagster, Streamlit, Cortex AI (tableau comparatif avec alternatives : Airbyte/Fivetran, Airflow, Power BI…).

## Chapitre 2 — Analyse et conception (4-6 p.)
1. Présentation du jeu de données Wide World Importers (domaines, schémas `Sales`, `Warehouse`, `Application`).
2. Besoins métiers : les 3 questions de la consigne + 3-5 KPI (CA, bénéfice, panier moyen, top clients/produits, ventes par mois/vendeur).
3. Tables sources retenues et pourquoi (tableau : table source → usage).
4. **Schéma d'architecture globale** (figure : SQL Server → DLT → Bronze → dbt Silver → dbt Gold → Cortex → Streamlit, Dagster autour).
5. Modèle Gold en étoile (figure : `fct_sales`, `fct_invoice_lines`, `dim_customers`, `dim_products`, `dim_salespeople`, `dim_date`).
6. Stratégie de chargement : full (`replace`) vs incrémental (`merge` sur `LastEditedWhen`).
7. Stratégie d'environnements : DuckDB (dev local, gratuit, rapide) → Snowflake (prod).

## Chapitre 3 — Mise en œuvre (8-12 p.) — le cœur du rapport
### 3.1 Environnement
WSL Ubuntu, Python 3.14, `uv`, `create-dagster` → **Captures 1-2**. Arborescence du projet → **Capture 4**.

### 3.2 Source SQL Server
Restauration de WWI, connexion `mssql+pymssql`.

### 3.3 Ingestion Bronze avec DLT
`dg scaffold defs dagster_dlt.DltLoadCollectionComponent` → **Capture 3**. Extrait de `loads.py` (tables, incrémental). Gestion des secrets (`.dlt/secrets.toml`, non versionné). Problèmes rencontrés : type `geography` (**Capture 6**), normalisation snake_case. Assets visibles dans Dagster → **Capture 7**.

### 3.4 Silver et Gold avec dbt
Structure du projet dbt, sources, macro `generate_schema_name`, règles de nettoyage (trim, cast, filtres), modèles Gold. Extraits SQL courts. Tests (`unique`, `not_null`, `relationships`) + résultat `dbt build`. Capture du **lineage dbt docs**.

### 3.5 Orchestration avec Dagster
`DbtProjectComponent`, graphe d'assets complet Bronze→Silver→Gold (capture), job `pipeline_complet`, schedule quotidien, un run réussi, asset checks.

### 3.6 Migration vers Snowflake
Script de création (rôle, warehouse, base, schémas), bascule par variables d'environnement (`DLT_DESTINATION`, `DBT_TARGET`), captures Snowsight des schémas BRONZE/SILVER/GOLD.

### 3.7 Application Text-to-SQL (Streamlit + Cortex)
Fonctionnement : question → prompt (schéma GOLD + règles) → `SNOWFLAKE.CORTEX.COMPLETE` → SQL → exécution → tableau/graphique. Garde-fous (SELECT seulement, LIMIT, rôle lecture seule). Captures des 3 questions de la consigne.

## Chapitre 4 — Résultats, tests et discussion (3-5 p.)
- Volumétrie par couche (nb de lignes par table).
- Résultats des tests de qualité.
- Évaluation Text-to-SQL : tableau d'une dizaine de questions → SQL généré correct ? résultat correct ? (taux de réussite).
- Temps d'exécution du pipeline (DuckDB vs Snowflake).
- Difficultés rencontrées et solutions (snake_case DLT, geography, chemins DuckDB, nommage des schémas, verrou DuckDB…).
- Limites (hallucinations du LLM, coût Snowflake, sécurité).

## Conclusion générale et perspectives (1-2 p.)
Bilan par objectif. Perspectives : Cortex Analyst + semantic model, CI/CD (GitHub Actions), snapshots dbt (SCD2), tableau de bord Power BI/Superset, déploiement Dagster+ / Streamlit in Snowflake, alerting.

## Bibliographie / webographie
Docs officielles : dlt, dbt, Dagster, Snowflake Cortex, Streamlit, Microsoft WWI ; Kimball (*The Data Warehouse Toolkit*) ; Databricks (architecture Médaillon).

## Annexes
Arborescence complète, `loads.py`, modèles dbt, `defs.yaml`, script Snowflake, `app.py`, guide d'installation.

---

### Conseils
- Une figure = un numéro + une légende + une phrase qui la commente dans le texte.
- Ne mettez **jamais** une capture contenant un mot de passe (Capture5 est à refaire en masquant les valeurs).
- Gardez les blocs de code courts dans le corps du texte ; le code complet va en annexe.
