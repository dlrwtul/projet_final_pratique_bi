import streamlit as st

import ui
from settings import PROJECT

PIPELINE = [
    ("SOURCE", "SQL Server"),
    ("BRONZE", "DLT"),
    ("SILVER · GOLD", "dbt"),
    ("ORCHESTRATION", "Dagster"),
    ("ENTREPÔT · IA", "Snowflake Cortex"),
    ("INTERFACE", "Streamlit"),
]


def render() -> None:
    brand_col, _, back_col = st.columns([4, 3, 2], vertical_alignment="center")
    brand_col.html(ui.brand())
    logged = "user" in st.session_state
    if back_col.button("← Espace d'analyse" if logged else "← Accueil", width="stretch"):
        ui.go("workspace" if logged else "landing")
    st.divider()

    text, logo = st.columns([1.8, 1], gap="large", vertical_alignment="center")
    text.html(f"""
        <div style="display:flex;flex-direction:column;gap:14px;padding:16px 0">
          <span class="wwi-eyebrow">À PROPOS DU PROJET</span>
          <h1 style="margin:0;font-size:36px;line-height:1.2;font-weight:600;color:{ui.NAVY}">{PROJECT['title']}</h1>
          <p style="margin:0;font-size:17px;line-height:1.6;color:{ui.MUTED}">
            De la base transactionnelle Wide World Importers (SQL Server) à une interface
            qui répond aux questions métier en langage naturel.</p>
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
    for col, (label, value) in zip(st.columns(4), facts):
        col.html(f'<div class="wwi-kpi" style="min-height:112px;box-sizing:border-box"><span>{label}</span>'
                 f'<strong style="font-size:18px">{value}</strong></div>')

    st.html(f'<h2 style="margin:40px 0 4px;font-size:22px;font-weight:600;color:{ui.NAVY}">Chaîne de traitement</h2>')
    for col, (step, tool) in zip(st.columns(len(PIPELINE)), PIPELINE):
        col.html(f'<div class="wwi-kpi" style="min-height:96px;box-sizing:border-box"><span style="font-family:\'IBM Plex Mono\',monospace;font-size:12px">'
                 f'{step}</span><strong style="font-size:16px">{tool}</strong></div>')

    st.divider()
    st.caption("Jeu de données : Wide World Importers (Microsoft) · FST · UCAD · Dakar")
