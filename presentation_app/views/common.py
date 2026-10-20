import streamlit as st

import session
import ui
from settings import PROJECT


def navbar(active: str) -> None:
    logged = session.user() is not None
    with st.container(key="navbar"):
        cols = st.columns([5, 1.1, 1.1, 1.5, 1.5], vertical_alignment="center")
        cols[0].html(ui.brand())
        if cols[1].button("Accueil", type="tertiary", width="stretch", disabled=active == "landing"):
            session.go("landing")
        if cols[2].button("À propos", type="tertiary", width="stretch", disabled=active == "about"):
            session.go("about")
        if logged:
            if cols[3].button("Mon espace", type="primary", width="stretch", icon=":material/dashboard:"):
                session.go("workspace")
            if cols[4].button("Déconnexion", width="stretch", icon=":material/logout:"):
                session.sign_out()
        else:
            if cols[3].button("Se connecter", width="stretch"):
                session.go("login")
            if cols[4].button("Créer un compte", type="primary", width="stretch"):
                st.session_state.auth_tab = "signup"
                session.go("login")
    st.divider()


def footer() -> None:
    st.divider()
    left, right = st.columns([3, 2], vertical_alignment="center")
    left.html(ui.ucad_block(detail=f"FST · {PROJECT['degree']} · {PROJECT['supervisor']}"))
    right.html(f'<div class="wwi-muted" style="text-align:right;font-size:13px">'
               f"Réalisé par {PROJECT['student']} · Données Wide World Importers</div>")
