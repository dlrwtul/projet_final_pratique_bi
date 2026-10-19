"""WWI Insight — application Text-to-SQL sur la couche Gold.

Lancement depuis la racine du projet :  streamlit run presentation_app/app.py
"""
import streamlit as st

import ui
import users_db
from views import about, landing, login, workspace

st.set_page_config(
    page_title="WWI Insight",
    page_icon=":material/public:",
    layout="wide",
    initial_sidebar_state="expanded",
)
ui.inject_css()
users_db.init()

page = st.session_state.get("page", "landing")
if page == "workspace" and "user" not in st.session_state:
    page = "login"

{"landing": landing, "login": login, "workspace": workspace, "about": about}[page].render()
