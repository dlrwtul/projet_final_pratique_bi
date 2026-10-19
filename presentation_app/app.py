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
    return re.sub(r"`{3}(sql)?", "", sql).strip().rstrip(";")


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