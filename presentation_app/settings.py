"""Configuration de l'application WWI Insight (variables d'environnement + infos projet)."""
import os
from pathlib import Path

APP_DIR = Path(__file__).parent
ROOT_DIR = APP_DIR.parent
ASSETS_DIR = APP_DIR / "assets"

# Base SQLite des comptes utilisateurs, dossiers et analyses (hors entrepôt).
USERS_DB_PATH = Path(os.getenv("APP_USERS_DB", APP_DIR / "data" / "users.db"))

# "snowflake" (Cortex AI) si les identifiants Snowflake sont présents, sinon "duckdb" (mode local).
BACKEND = os.getenv("APP_BACKEND") or ("snowflake" if os.getenv("SF_ACCOUNT") else "duckdb")
# expandvars/expanduser : un fichier .env ne remplace pas $HOME ni ~.
DUCKDB_PATH = os.path.expanduser(os.path.expandvars(os.getenv("DUCKDB_PATH", str(ROOT_DIR / "warehouse.duckdb"))))

SNOWFLAKE = {
    "account": os.getenv("SF_ACCOUNT"),
    "user": os.getenv("SF_USER"),
    "password": os.getenv("SF_PASSWORD"),
    "role": os.getenv("SF_ROLE", "PFPB_ROLE"),
    "warehouse": os.getenv("SF_WAREHOUSE", "COMPUTE_WH"),
    "database": os.getenv("SF_DATABASE", "PROJET_FINAL_PRATIQUE_BI"),
    "schema": "GOLD",
}
CORTEX_MODEL = os.getenv("CORTEX_MODEL", "mistral-large2")

# Génération du SQL : "auto" (Cortex si disponible, sinon Ollama), "cortex", "ollama" ou "none".
# Cortex COMPLETE n'est pas disponible sur les comptes d'essai Snowflake : Ollama sert de repli local.
SQL_GENERATOR = os.getenv("SQL_GENERATOR", "auto")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")

MAX_ROWS = 1000

# Informations affichées dans la page « À propos ».
PROJECT = {
    "title": "Conception d'une Modern Data Platform avec architecture Médaillon "
             "et application Text-to-SQL basée sur l'IA",
    "student": "Ibrahima Lang Diop",
    "supervisor": "Dr. Jean Gane SARR",
    "degree": "Master 2 Business Intelligence",
    "department": "Maths-Info · Section Informatique",
    "faculty": "Faculté des Sciences et Techniques",
    "university": "Université Cheikh Anta Diop de Dakar",
    "academic_year": "",
}
