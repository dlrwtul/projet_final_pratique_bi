import streamlit as st

import session
import ui
import warehouse
from views.common import footer, navbar

HERO_EXAMPLES = {
    "Quels sont les dix meilleurs clients par chiffre d'affaires ?": "Top 10 clients",
    "Quel est le montant total des ventes par mois ?": "Ventes par mois",
    "Quels produits génèrent le plus de bénéfices ?": "Produits les plus rentables",
    "Quel est le chiffre d'affaires par vendeur ?": "CA par vendeur",
}
MONTHLY = "Quel est le montant total des ventes par mois ?"


@st.cache_data(ttl=3600, show_spinner=False)
def _monthly_sales():
    try:
        return warehouse.run_sql(warehouse.EXAMPLES[MONTHLY])
    except warehouse.QueryError:
        return None


def _pick_example() -> None:
    question = st.session_state.get("hero_pills")
    if question:
        st.session_state.hero_pills = None
        st.session_state.pending_question = question
        st.session_state.page = "workspace" if session.user() else "login"
        st.query_params["p"] = st.session_state.page


def _hero() -> None:
    _, center, _ = st.columns([1, 4, 1])
    with center:
        st.html(f"""
            <div style="text-align:center;padding:40px 0 8px;display:flex;flex-direction:column;align-items:center;gap:18px">
              <span class="wwi-eyebrow">TEXT-TO-SQL · SNOWFLAKE · IA</span>
              <h1 style="margin:0;font-size:52px;line-height:1.08;font-weight:700;letter-spacing:-.02em;color:{ui.NAVY}">
                Posez la question.<br><span style="color:{ui.OCEAN}">Les données répondent.</span></h1>
              <p style="margin:0;max-width:560px;font-size:18px;line-height:1.6;color:{ui.MUTED}">
                Les ventes de Wide World Importers, interrogées en français. Le SQL est écrit pour vous.</p>
            </div>""")
        with st.container(key="hero_search"):
            with st.form("hero_form", border=False):
                field, submit = st.columns([6, 1.4], vertical_alignment="center")
                question = field.text_input("Votre question", label_visibility="collapsed",
                                            placeholder="Ex. : Quels produits génèrent le plus de bénéfices ?")
                if submit.form_submit_button("Analyser", type="primary", width="stretch",
                                             icon=":material/arrow_forward:") and question.strip():
                    session.ask_later(question.strip())
        with st.container(key="hero_pills_box"):
            st.pills("Exemples", list(HERO_EXAMPLES), format_func=HERO_EXAMPLES.get, key="hero_pills",
                     label_visibility="collapsed", on_change=_pick_example)


def _overview() -> None:
    kpi = warehouse.key_figures()
    period = f"{kpi['debut']:%m/%Y} – {kpi['fin']:%m/%Y}" if kpi and hasattr(kpi["debut"], "strftime") else ""
    st.html(f'<h2 style="margin:40px 0 4px;font-size:22px;font-weight:600;color:{ui.NAVY}">'
            f'En direct de la couche Gold <span class="wwi-muted" style="font-weight:400;font-size:16px">'
            f"· {period}</span></h2>")
    chart_col, kpi_col = st.columns([1.6, 1], gap="medium")
    with chart_col, st.container(border=True):
        st.html(f'<span style="font-size:14px;font-weight:600;color:{ui.NAVY}">Chiffre d\'affaires HT par mois</span>')
        df = _monthly_sales()
        figure = ui.chart(df, height=230) if df is not None else None
        if figure is not None:
            st.altair_chart(figure, width="stretch")
    cards = [
        ("Chiffre d'affaires HT", ui.money(kpi and kpi["ca"])),
        ("Bénéfice", ui.money(kpi and kpi["benefice"])),
        ("Commandes", ui.integer(kpi and kpi["commandes"])),
        ("Clients · Produits", f"{ui.integer(kpi and kpi['clients'])} · {ui.integer(kpi and kpi['produits'])}"),
    ]
    with kpi_col:
        for row in (cards[:2], cards[2:]):
            for col, (label, value) in zip(st.columns(2), row):
                col.html(f'<div class="wwi-kpi"><span>{label}</span><strong>{value}</strong></div>')


def _steps() -> None:
    steps = [
        ("Vous posez la question", "En français, comme à un collègue."),
        ("L'IA écrit le SQL", "Sur le schéma Gold, toujours visible et en lecture seule."),
        ("Vous lisez la réponse", "Graphique, tableau, export CSV, rangés dans vos dossiers."),
    ]
    st.html('<div style="height:12px"></div>')
    for i, (col, (title, text)) in enumerate(zip(st.columns(3), steps), start=1):
        col.html(f'<div class="wwi-step"><b>{i}</b><h4>{title}</h4><p>{text}</p></div>')


def render() -> None:
    navbar("landing")
    _hero()
    _overview()
    _steps()
    footer()
