import streamlit as st

import session
import ui
import users_db

MODES = {"login": "Connexion", "signup": "Inscription"}


def render() -> None:
    _, center, _ = st.columns([1, 1.15, 1])
    with center:
        st.html(f'<div style="display:flex;justify-content:center;padding:48px 0 20px">{ui.brand(size=34)}</div>')
        with st.container(key="auth_card"):
            mode = st.segmented_control("Accès", list(MODES), format_func=MODES.get, width="stretch",
                                        default=st.session_state.pop("auth_tab", "login"),
                                        key="auth_mode", label_visibility="collapsed") or "login"
            signup = mode == "signup"
            st.html(f'<h1 style="margin:14px 0 2px;font-size:26px;font-weight:600;color:{ui.NAVY}">'
                    f'{"Créer un compte" if signup else "Bon retour"}</h1>'
                    f'<p class="wwi-muted" style="margin:0 0 6px">'
                    f'{"Vos dossiers d’analyse vous attendent." if signup else "Connectez-vous à votre espace."}</p>')
            if pending := st.session_state.get("pending_question"):
                st.info(f"Votre question sera lancée juste après : « {pending} »", icon=":material/schedule:")

            with st.form(f"form_{mode}", border=False):
                name = st.text_input("Nom complet", placeholder="Prénom Nom") if signup else ""
                email = st.text_input("Adresse e-mail", placeholder="vous@exemple.sn")
                password = st.text_input("Mot de passe", type="password",
                                         placeholder="8 caractères minimum" if signup else "")
                submitted = st.form_submit_button("Créer mon compte" if signup else "Se connecter",
                                                  type="primary", width="stretch")
            if submitted:
                try:
                    account = (users_db.create_user(name, email, password) if signup
                               else users_db.authenticate(email, password))
                except users_db.AuthError as exc:
                    st.error(str(exc))
                else:
                    session.sign_in(account)

        _, back, _ = st.columns([1, 2, 1])
        if back.button("Retour à l'accueil", type="tertiary", icon=":material/arrow_back:", width="stretch"):
            session.go("landing")
