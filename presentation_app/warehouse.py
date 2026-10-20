"""Accès à la couche Gold : génération SQL (Snowflake Cortex ou Ollama), contrôle et exécution."""
import json
import re
import urllib.request
from datetime import date
from decimal import Decimal

import pandas as pd
import streamlit as st

from settings import (BACKEND, CORTEX_MODEL, DUCKDB_PATH, MAX_ROWS, OLLAMA_MODEL, OLLAMA_URL,
                      SNOWFLAKE, SQL_GENERATOR)

IS_SNOWFLAKE = BACKEND == "snowflake"

# Questions d'exemple, regroupées par thème, avec leur SQL (compatible DuckDB et Snowflake).
# Les trois premières sont celles de la consigne. Sans modèle d'IA disponible, ce sont les
# seules questions auxquelles l'application sait répondre.
EXAMPLE_GROUPS = {
    "Ventes": {
        "Quels sont les dix meilleurs clients par chiffre d'affaires ?": """
select c.customer_name, sum(s.sales_amount_excl_tax) as chiffre_affaires
from gold.fct_sales s
join gold.dim_customers c on s.customer_id = c.customer_id
group by c.customer_name
order by chiffre_affaires desc
limit 10""",
        "Quel est le montant total des ventes par mois ?": """
select date_trunc('month', order_date) as mois, sum(sales_amount_excl_tax) as chiffre_affaires
from gold.fct_sales
group by 1
order by 1""",
        "Quel est le chiffre d'affaires par année ?": """
select extract(year from order_date) as annee, sum(sales_amount_excl_tax) as chiffre_affaires
from gold.fct_sales
group by 1
order by 1""",
        "Quel est le chiffre d'affaires par vendeur ?": """
select sp.salesperson_name, sum(s.sales_amount_excl_tax) as chiffre_affaires
from gold.fct_sales s
join gold.dim_salespeople sp on s.salesperson_id = sp.salesperson_id
group by sp.salesperson_name
order by chiffre_affaires desc""",
    },
    "Produits": {
        "Quels produits génèrent le plus de bénéfices ?": """
select p.product_name, sum(f.line_profit) as benefice
from gold.fct_invoice_lines f
join gold.dim_products p on f.product_id = p.product_id
group by p.product_name
order by benefice desc
limit 10""",
        "Quels sont les produits les plus vendus en quantité ?": """
select p.product_name, sum(s.quantity) as quantite_vendue
from gold.fct_sales s
join gold.dim_products p on s.product_id = p.product_id
group by p.product_name
order by quantite_vendue desc
limit 10""",
    },
    "Rentabilité": {
        "Quel est le bénéfice par année ?": """
select extract(year from invoice_date) as annee, sum(line_profit) as benefice
from gold.fct_invoice_lines
group by 1
order by 1""",
        "Quel est le panier moyen par année ?": """
select extract(year from order_date) as annee,
       sum(sales_amount_excl_tax) / count(distinct order_id) as panier_moyen
from gold.fct_sales
group by 1
order by 1""",
    },
}
EXAMPLES = {q: sql for group in EXAMPLE_GROUPS.values() for q, sql in group.items()}

FORBIDDEN = re.compile(
    r"\b(insert|update|delete|merge|drop|alter|create|truncate|grant|revoke|"
    r"copy|put|call|execute|attach|detach|install|pragma)\b",
    re.IGNORECASE,
)


class QueryError(Exception):
    pass


# --- Connexion ----------------------------------------------------------------

@st.cache_resource(show_spinner=False)
def _snowflake_connection():
    import snowflake.connector

    # keep_alive : la connexion est gardée en cache tant que l'application tourne.
    return snowflake.connector.connect(**SNOWFLAKE, client_session_keep_alive=True)


def _execute(sql: str, params: tuple = ()) -> pd.DataFrame:
    if IS_SNOWFLAKE:
        cur = _snowflake_connection().cursor()
        try:
            cur.execute(sql, params)
            rows = cur.fetchmany(MAX_ROWS)
            cols = [d[0].lower() for d in cur.description]
        finally:
            cur.close()
        df = pd.DataFrame(rows, columns=cols)
    else:
        import duckdb

        # Connexion en lecture seule ouverte à chaque requête : n'empêche pas le pipeline d'écrire.
        con = duckdb.connect(DUCKDB_PATH, read_only=True)
        try:
            df = con.execute(sql, list(params)).fetch_df().head(MAX_ROWS)
        finally:
            con.close()
        df.columns = [c.lower() for c in df.columns]
    # Les NUMBER/DECIMAL arrivent en objets Decimal et les DATE Snowflake en objets date :
    # on les convertit pour les tableaux et les graphiques.
    for col in df.columns:
        first = df[col].dropna().head(1)
        if not first.empty and isinstance(first.iloc[0], Decimal):
            df[col] = df[col].astype(float)
        elif not first.empty and isinstance(first.iloc[0], date):
            df[col] = pd.to_datetime(df[col])
    return df


def backend_label() -> str:
    source = "SNOWFLAKE" if IS_SNOWFLAKE else "DUCKDB LOCAL"
    model = {"cortex": f"cortex/{CORTEX_MODEL}", "ollama": f"ollama/{OLLAMA_MODEL}"}.get(generator(), "exemples")
    return f"{source} · GOLD · {model}"


# --- Schéma et génération -----------------------------------------------------

@st.cache_data(ttl=3600, show_spinner=False)
def gold_schema() -> str:
    df = _execute(
        "select table_name, column_name, data_type from information_schema.columns "
        "where lower(table_schema) = 'gold' order by table_name, ordinal_position"
    )
    return "\n".join(
        f"gold.{t.lower()}({', '.join(f'{c.lower()} {d}' for c, d in zip(g.column_name, g.data_type))})"
        for t, g in df.groupby("table_name")
    )


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


def _normalise(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def example_sql(question: str) -> str | None:
    wanted = _normalise(question)
    for q, sql in EXAMPLES.items():
        if _normalise(q) == wanted:
            return sql.strip()
    return None


def _cortex(prompt: str) -> str:
    df = _execute("select snowflake.cortex.complete(%s, %s) as sql", (CORTEX_MODEL, prompt))
    return df.iloc[0, 0]


def _ollama(prompt: str, timeout: int = 180) -> str:
    body = json.dumps({"model": OLLAMA_MODEL, "prompt": prompt, "stream": False,
                       "options": {"temperature": 0}}).encode()
    req = urllib.request.Request(f"{OLLAMA_URL}/api/generate", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)["response"]


def _cortex_available() -> bool:
    if not IS_SNOWFLAKE:
        return False
    try:
        _cortex("Réponds OK.")
        return True
    except Exception:  # compte d'essai, modèle absent de la région, droit CORTEX_USER manquant…
        return False


def _ollama_available() -> bool:
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=2) as resp:
            models = [m["name"] for m in json.load(resp).get("models", [])]
    except Exception:
        return False
    return any(m == OLLAMA_MODEL or m.split(":")[0] == OLLAMA_MODEL for m in models)


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
        return "ollama"
    return None


def generate_sql(question: str) -> str:
    sql = example_sql(question)
    if sql:
        return sql
    engine = generator()
    if engine is None:
        raise QueryError(
            "Aucun modèle d'IA disponible (Cortex indisponible, Ollama non démarré). "
            "Choisissez une question d'exemple ou écrivez directement le SQL."
        )
    prompt = PROMPT.format(dialect="Snowflake" if IS_SNOWFLAKE else "DuckDB",
                           schema=gold_schema(), max_rows=MAX_ROWS, question=question)
    try:
        answer = _cortex(prompt) if engine == "cortex" else _ollama(prompt)
    except Exception as exc:
        raise QueryError(f"Le modèle {engine} n'a pas répondu : {exc}") from exc
    return extract_sql(answer)


def extract_sql(answer: str) -> str:
    """Isole la requête quand le modèle l'entoure de texte ou d'un bloc ```sql."""
    block = re.search(r"```(?:sql)?\s*(.*?)```", answer, re.IGNORECASE | re.DOTALL)
    if block:
        answer = block.group(1)
    start = re.search(r"\b(with|select)\b", answer, re.IGNORECASE)
    if start:
        answer = answer[start.start():]
    return answer.split(";")[0].strip()


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


def run_sql(sql: str) -> pd.DataFrame:
    try:
        return _execute(sql)
    except Exception as exc:  # erreur SQL renvoyée par le moteur
        raise QueryError(f"Erreur d'exécution : {exc}") from exc


# --- Chiffres clés (page d'accueil) -------------------------------------------

@st.cache_data(ttl=3600, show_spinner=False)
def key_figures() -> dict | None:
    try:
        df = _execute("""
            select
                (select sum(sales_amount_excl_tax) from gold.fct_sales) as ca,
                (select sum(line_profit) from gold.fct_invoice_lines) as benefice,
                (select count(distinct order_id) from gold.fct_sales) as commandes,
                (select count(*) from gold.dim_customers) as clients,
                (select count(*) from gold.dim_products) as produits,
                (select min(order_date) from gold.fct_sales) as debut,
                (select max(order_date) from gold.fct_sales) as fin
        """)
    except Exception:
        return None
    return df.iloc[0].to_dict()
