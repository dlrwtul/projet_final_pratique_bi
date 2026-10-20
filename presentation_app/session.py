"""Navigation entre pages et session utilisateur persistante.

La page courante (?p=…) et le jeton de session (?s=…) sont gardés dans l'URL : un rechargement
du navigateur ne déconnecte plus l'utilisateur et le ramène sur la même page.
"""
import streamlit as st

import users_db

PAGES = ("landing", "login", "workspace", "about")


def restore() -> None:
    if "user" not in st.session_state and (token := st.query_params.get("s")):
        user = users_db.session_user(token)
        if user:
            st.session_state.user, st.session_state.token = user, token
        else:
            del st.query_params["s"]
    if "page" not in st.session_state:
        page = st.query_params.get("p", "landing")
        st.session_state.page = page if page in PAGES else "landing"


def current_page() -> str:
    page = st.session_state.page
    if page == "workspace" and "user" not in st.session_state:
        return "login"
    if page == "login" and "user" in st.session_state:
        return "workspace"
    return page


def go(page: str) -> None:
    st.session_state.page = page
    st.query_params["p"] = page
    st.rerun()


def user() -> dict | None:
    return st.session_state.get("user")


def sign_in(account: dict) -> None:
    token = users_db.create_session(account["id"])
    st.session_state.user, st.session_state.token = account, token
    st.session_state.pop("folder_id", None)
    st.query_params["s"] = token
    go("workspace")


def sign_out() -> None:
    if token := st.session_state.get("token"):
        users_db.delete_session(token)
    st.session_state.clear()
    st.query_params.clear()
    go("landing")


def ask_later(question: str) -> None:
    """Mémorise une question posée depuis l'accueil : elle sera lancée dans l'espace d'analyse."""
    st.session_state.pending_question = question
    go("workspace" if user() else "login")
