import streamlit as st

import ui
from settings import PROJECT
from views.common import footer, navbar

PIPELINE = [
    ("SOURCE", "SQL Server", "Wide World Importers"),
    ("BRONZE", "DLT", "Ingestion incrémentale"),
    ("SILVER · GOLD", "dbt", "Nettoyage, étoile, tests"),
    ("ORCHESTRATION", "Dagster", "Lignage et planification"),
    ("ENTREPÔT · IA", "Snowflake", "Cortex / Ollama"),
    ("INTERFACE", "Streamlit", "Text-to-SQL"),
]


def render() -> None:
    navbar("about")

    text, logo = st.columns([1.8, 1], gap="large", vertical_alignment="center")
    text.html(f"""
        <div style="display:flex;flex-direction:column;gap:14px;padding:20px 0 8px">
          <span><span class="wwi-eyebrow">PROJET DE FIN DE MODULE · M2 BI</span></span>
          <h1 style="margin:0;font-size:34px;line-height:1.2;font-weight:600;color:{ui.NAVY}">{PROJECT['title']}</h1>
        </div>""")
    logo.html(f"""
        <div style="display:flex;align-items:center;gap:16px">
          <img src="{ui.emblem_uri()}" alt="Emblème de l'Université Cheikh Anta Diop de Dakar"
               style="width:96px;height:96px;flex:none">
          <div style="display:flex;flex-direction:column;gap:4px">
            <span style="font-size:18px;font-weight:600;line-height:1.3;color:{ui.NAVY}">{PROJECT['university']}</span>
            <span style="font-size:14px;color:{ui.MUTED}">{PROJECT['faculty']}</span>
          </div>
        </div>""")

    degree = PROJECT["degree"] + (f" · {PROJECT['academic_year']}" if PROJECT["academic_year"] else "")
    facts = [
        ("Réalisé par", PROJECT["student"]),
        ("Encadrant", PROJECT["supervisor"]),
        ("Formation", degree),
        ("Département", PROJECT["department"]),
    ]
    st.html('<div style="height:8px"></div>')
    for col, (label, value) in zip(st.columns(4), facts):
        col.html(f'<div class="wwi-kpi"><span>{label}</span><strong style="font-size:18px">{value}</strong></div>')

    st.html(f'<h2 style="margin:36px 0 4px;font-size:22px;font-weight:600;color:{ui.NAVY}">Architecture</h2>')
    for i, (col, (step, tool, detail)) in enumerate(zip(st.columns(len(PIPELINE)), PIPELINE), start=1):
        col.html(f'<div class="wwi-step"><b>{i}</b>'
                 f'<div style="font-family:\'IBM Plex Mono\',monospace;font-size:11px;color:{ui.MUTED}">{step}</div>'
                 f'<h4 style="margin-top:2px">{tool}</h4><p>{detail}</p></div>')
    footer()
