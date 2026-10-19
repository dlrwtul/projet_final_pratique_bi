import streamlit as st

import ui
import users_db


def _sign_in(user: dict) -> None:
    st.session_state.user = user
    st.session_state.pop("folder_id", None)
    ui.go("workspace")


def render() -> None:
    panel, form = st.columns([1, 1], gap="large")

    with panel:
        st.html(f"""
            <div style="background:{ui.NAVY};border-radius:10px;padding:36px 40px;min-height:540px;
                        box-sizing:border-box;display:flex;flex-direction:column;justify-content:space-between;gap:40px">
              {ui.brand(dark=True)}
              <div style="display:flex;flex-direction:column;gap:16px">
                <span style="font-family:'IBM Plex Mono',monospace;font-size:13px;color:#5FB4D9">
                  &gt; montant total des ventes par mois ?</span>
                <p style="margin:0;font-size:28px;line-height:1.3;font-weight:500;color:#FFFFFF">
                  Vos questions, vos dossiers et vos résultats, conservés d'une session à l'autre.</p>
                <p style="margin:0;font-size:15px;line-height:1.6;color:#A9B6C6">
                  Mots de passe hachés (bcrypt). Comptes et dossiers stockés à part de l'entrepôt.</p>
              </div>
              {ui.ucad_block(size=40, dark=True)}
            </div>""")

    with form:
        st.html(f'<div style="padding-top:48px"><h1 style="margin:0;font-size:28px;font-weight:600;color:{ui.NAVY}">'
                f'Bienvenue</h1><p class="wwi-muted" style="margin:6px 0 0">'
                "Connectez-vous pour retrouver vos dossiers d'analyse.</p></div>")
        login_tab, signup_tab = st.tabs(["Connexion", "Inscription"])

        with login_tab, st.form("login", border=False):
            email = st.text_input("Adresse e-mail", placeholder="vous@exemple.sn", key="login_email")
            password = st.text_input("Mot de passe", type="password", key="login_password")
            if st.form_submit_button("Se connecter", type="primary", width="stretch"):
                try:
                    _sign_in(users_db.authenticate(email, password))
                except users_db.AuthError as exc:
                    st.error(str(exc))

        with signup_tab, st.form("signup", border=False):
            full_name = st.text_input("Nom complet", placeholder="Prénom Nom", key="signup_name")
            email = st.text_input("Adresse e-mail", placeholder="vous@exemple.sn", key="signup_email")
            password = st.text_input("Mot de passe", type="password", placeholder="8 caractères minimum", key="signup_password")
            if st.form_submit_button("Créer mon compte", type="primary", width="stretch"):
                try:
                    _sign_in(users_db.create_user(full_name, email, password))
                except users_db.AuthError as exc:
                    st.error(str(exc))

        if st.button("← Retour à l'accueil", type="tertiary"):
            ui.go("landing")
