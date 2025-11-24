# app.py

"""
Main application entry point.
Contains:
- page layout config
- sidebar router
- authentication gate
- page dispatch to the pages/ modules
"""

import streamlit as st

from utils.auth import login, logout
from utils.db import fetch_table
from settings.constants import (
    TABLE_DIPENDENTI,
    TABLE_RICHIESTE,
    APP_TITLE
)

from views.home import render_home
from views.dipendenti import render_dipendenti
from views.richieste import render_richieste


# ------------------------------------------------------------
# INITIAL STREAMLIT CONFIG
# ------------------------------------------------------------
st.set_page_config(
    page_title=APP_TITLE,
    layout="wide",
    initial_sidebar_state="expanded"
)


# ------------------------------------------------------------
# MAIN ROUTER
# ------------------------------------------------------------
def main_app():
    # Sidebar
    st.sidebar.title("Menu")
    st.sidebar.write(f"👤 {st.session_state.get('user_email', '')}")

    if st.sidebar.button("Logout"):
        logout()
        st.rerun()

    section = st.sidebar.radio(
        "Seleziona sezione",
        ["Home", "Dipendenti", "Richieste ferie"],
        index=0
    )

    dip_action = None
    req_action = None

    # Submenus
    if section == "Dipendenti":
        st.sidebar.markdown("### Azioni dipendenti")
        dip_action = st.sidebar.radio(
            "Azione",
            ["Vista & download", "Aggiungi singolo", "Import", "Modifica / Elimina"],
            index=0
        )

    if section == "Richieste ferie":
        st.sidebar.markdown("### Azioni richieste ferie")
        req_action = st.sidebar.radio(
            "Azione",
            ["Vista & download", "Nuova richiesta", "Modifica / Elimina"],
            index=0
        )

    # --------------------------------------------------------
    # DATA FETCH (only once per load)
    # --------------------------------------------------------
    df_dip = fetch_table(TABLE_DIPENDENTI)
    df_req = fetch_table(TABLE_RICHIESTE)

    # --------------------------------------------------------
    # PAGE DISPATCH
    # --------------------------------------------------------
    if section == "Home":
        render_home(df_dip, df_req)

    elif section == "Dipendenti":
        render_dipendenti(df_dip, dip_action)

    elif section == "Richieste ferie":
        render_richieste(df_req, req_action)


# ------------------------------------------------------------
# AUTH GATE
# ------------------------------------------------------------
def main():
    # User not logged in → show login form
    if "access_token" not in st.session_state:
        st.title(f"{APP_TITLE} – Accedi")

        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")

            if submitted:
                if login(email, password):
                    st.rerun()

        st.stop()

    # User authenticated → show app
    else:
        main_app()


# ------------------------------------------------------------
# ENTRY POINT
# ------------------------------------------------------------
if __name__ == "__main__":
    main()
