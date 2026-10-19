import streamlit as st

import ui
import warehouse
from settings import PROJECT

PREVIEW_QUESTION = "Quels sont les dix meilleurs clients par chiffre d'affaires ?"


@st.cache_data(ttl=3600, show_spinner=False)
def _preview():
    try:
        return warehouse.run_sql(warehouse.EXAMPLES[PREVIEW_QUESTION]).head(5)
    except warehouse.QueryError:
        return None


def _header() -> None:
    brand_col, _, about_col, login_col = st.columns([4, 3, 1.2, 1.4], vertical_alignment="center")
    brand_col.html(ui.brand())
    if about_col.button("À propos", type="tertiary", width="stretch"):
        ui.go("about")
    logged = "user" in st.session_state
    if login_col.button("Mon espace" if logged else "Se connecter", type="primary", width="stretch"):
        ui.go("workspace" if logged else "login")
    st.divider()


def render() -> None:
    _header()

    left, right = st.columns([1.1, 1], gap="large", vertical_alignment="center")
    with left:
        st.html(f"""
            <div style="display:flex;flex-direction:column;gap:18px;padding:24px 0 8px">
              <span class="wwi-eyebrow">TEXT-TO-SQL · SNOWFLAKE CORTEX AI</span>
              <h1 style="margin:0;font-size:46px;line-height:1.12;font-weight:600;letter-spacing:-.015em;color:{ui.NAVY}">
                Les ventes de Wide World Importers, interrogées en langage naturel.</h1>
              <p style="margin:0;font-size:18px;line-height:1.6;color:{ui.MUTED}">
                Clients, produits, vendeurs, facturation : posez votre question en français,
                obtenez la requête SQL et le résultat issus de la couche Gold.</p>
            </div>""")
        b1, b2, _ = st.columns([1.3, 1.3, 1])
        if b1.button("Commencer l'analyse", type="primary", width="stretch"):
            ui.go("workspace" if "user" in st.session_state else "login")
        if b2.button("À propos du projet", width="stretch"):
            ui.go("about")

    with right:
        with st.container(border=True):
            st.markdown(f"**{PREVIEW_QUESTION}**")
            st.code(warehouse.EXAMPLES[PREVIEW_QUESTION].strip(), language="sql")
            df = _preview()
            if df is not None:
                st.dataframe(df, hide_index=True, width="stretch",
                             column_config={"chiffre_affaires": st.column_config.NumberColumn(format="localized")})

    kpi = warehouse.key_figures()
    period = ""
    if kpi:
        period = f" · {kpi['debut']:%m/%Y} – {kpi['fin']:%m/%Y}" if hasattr(kpi["debut"], "strftime") else ""
    st.html(f'<h2 style="margin:48px 0 0;font-size:24px;font-weight:600;color:{ui.NAVY}">'
            f"Le périmètre analysé{period}</h2>")
    cards = [
        ("Chiffre d'affaires HT", ui.money(kpi and kpi["ca"])),
        ("Bénéfice facturé", ui.money(kpi and kpi["benefice"])),
        ("Commandes", ui.integer(kpi and kpi["commandes"])),
        ("Clients · Produits", f"{ui.integer(kpi and kpi['clients'])} · {ui.integer(kpi and kpi['produits'])}"),
    ]
    for col, (label, value) in zip(st.columns(4), cards):
        col.html(f'<div class="wwi-kpi"><span>{label}</span><strong>{value}</strong></div>')
    if kpi is None:
        st.caption("Chiffres indisponibles : l'entrepôt n'est pas joignable.")

    tables = ["fct_sales", "fct_invoice_lines", "dim_customers", "dim_products", "dim_salespeople", "dim_date"]
    st.html('<div style="margin-top:8px"><span class="wwi-muted" style="font-size:14px;margin-right:8px">'
            "Tables Gold :</span>" + "".join(f'<span class="wwi-chip">{t}</span>' for t in tables) + "</div>")

    st.divider()
    st.html(ui.ucad_block(detail=f"FST · {PROJECT['degree']} · {PROJECT['supervisor']}"))
