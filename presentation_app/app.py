"""WWI Insight — application Text-to-SQL sur la couche Gold.

Lancement depuis la racine du projet :  streamlit run presentation_app/app.py
"""
import streamlit as st

import session
import ui
import users_db
from views import about, landing, login, workspace

st.set_page_config(
    page_title="WWI Insight",
    page_icon=":material/public:",
    layout="wide",
    initial_sidebar_state="expanded",
)
users_db.init()
session.restore()

page = session.current_page()
ui.inject_css(background=ui.SURFACE if page == "login" else "#FFFFFF",
              max_width=980 if page == "workspace" else 1180)
{"landing": landing, "login": login, "workspace": workspace, "about": about}[page].render()
