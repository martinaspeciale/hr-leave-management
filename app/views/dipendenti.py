# pages/dipendenti.py

"""
Page: Gestione Dipendenti
CRUD operations for the "dipendenti" table.
"""

import streamlit as st
import pandas as pd

from utils.db import db_insert, db_update, db_delete
from utils.exports import (
    df_to_excel_bytes,
    df_to_csv_bytes,
    df_to_json_bytes
)
from settings.constants import TABLE_DIPENDENTI


# -------------------------------------------------------------
# PAGE DISPATCHER
# -------------------------------------------------------------
def render_dipendenti(df_dip: pd.DataFrame, action: str):
    st.title("Gestione Dipendenti")

    if df_dip is None:
        df_dip = pd.DataFrame()

    if action == "Vista & download":
        _page_vista(df_dip)

    elif action == "Aggiungi singolo":
        _page_add()

    elif action == "Import":
        _page_import()

    elif action == "Modifica / Elimina":
        _page_edit_delete(df_dip)


# -------------------------------------------------------------
# VISTA + DOWNLOAD
# -------------------------------------------------------------
def _page_vista(df: pd.DataFrame):
    st.subheader("Elenco dipendenti")
    st.dataframe(df)

    st.subheader("Scarica tabella dipendenti")

    fmt = st.radio(
        "Formato file",
        ["Excel (.xlsx)", "CSV (.csv)", "JSON (.json)"],
        horizontal=True,
    )

    if fmt == "Excel (.xlsx)":
        data = df_to_excel_bytes(df)
        fname = "dipendenti.xlsx"
        mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    elif fmt == "CSV (.csv)":
        data = df_to_csv_bytes(df)
        fname = "dipendenti.csv"
        mime = "text/csv"

    else:  # JSON
        data = df_to_json_bytes(df)
        fname = "dipendenti.json"
        mime = "application/json"

    st.download_button("📥 Scarica", data=data, file_name=fname, mime=mime)


# -------------------------------------------------------------
# AGGIUNGI SINGOLO DIPENDENTE
# -------------------------------------------------------------
def _page_add():
    st.subheader("Aggiungi un nuovo dipendente")

    with st.form("add_dip"):
        email = st.text_input("Email")
        nome = st.text_input("Nome")
        cognome = st.text_input("Cognome")
        business_unit = st.text_input("Business Unit")
        office_location = st.text_input("Office Location")
        level = st.text_input("Level")

        submitted = st.form_submit_button("Aggiungi")

        if submitted:
            payload = {
                "email": email,
                "nome": nome,
                "cognome": cognome,
                "business_unit": business_unit,
                "office_location": office_location,
                "level": level,
            }

            r = db_insert(TABLE_DIPENDENTI, payload)
            if r.status_code < 300:
                st.success("Dipendente aggiunto con successo!")
            else:
                st.error(f"❌ Errore: {r.text}")


# -------------------------------------------------------------
# IMPORT MASSIVO
# -------------------------------------------------------------
def _page_import():
    st.subheader("Importa dipendenti da file")

    file = st.file_uploader("Carica file (.xlsx o .csv)", type=["xlsx", "csv"])

    if not file:
        return

    # Load file
    if file.name.endswith(".csv"):
        df_up = pd.read_csv(file)
    else:
        df_up = pd.read_excel(file)

    df_up = df_up.replace({pd.NA: None, "None": None, "nan": None})
    df_up = df_up.where(pd.notnull(df_up), None)

    df_prev = df_up.drop(columns=["last_updated"], errors="ignore")
    st.write("📄 Anteprima file:")
    st.dataframe(df_prev)

    if st.button("Importa nel database"):
        successes = 0
        failures = []

        for _, row in df_up.iterrows():
            payload = {
                k: (None if pd.isna(v) or v in ["", "nan", "None"] else v)
                for k, v in row.to_dict().items()
            }
            payload.pop("last_updated", None)

            r = db_insert(TABLE_DIPENDENTI, payload)

            if r.status_code < 300:
                successes += 1
            else:
                failures.append({"row": payload, "error": r.text})

        st.success(f"Import completato! {successes} record inseriti.")

        if failures:
            st.error("Alcuni record non sono stati importati:")
            st.json(failures)


# -------------------------------------------------------------
# MODIFICA / ELIMINA DIPENDENTE
# -------------------------------------------------------------
def _page_edit_delete(df: pd.DataFrame):
    st.subheader("Modifica o elimina dipendente")

    if df.empty:
        st.info("Nessun dipendente presente.")
        return

    df = df.copy()
    df["label"] = df.apply(
        lambda r: f"{r.get('nome', '')} {r.get('cognome', '')} ({r.get('email', '')})",
        axis=1,
    )

    selected = st.selectbox("Seleziona dipendente", df["label"])
    row = df[df["label"] == selected].iloc[0]
    email_pk = row["email"]

    with st.form("edit_dip"):
        nome = st.text_input("Nome", value=row.get("nome", ""))
        cognome = st.text_input("Cognome", value=row.get("cognome", ""))
        bu = st.text_input("Business Unit", value=row.get("business_unit", ""))
        loc = st.text_input("Office Location", value=row.get("office_location", ""))
        level = st.text_input("Level", value=row.get("level", ""))

        submitted = st.form_submit_button("Salva modifiche")

        if submitted:
            payload = {
                "nome": nome,
                "cognome": cognome,
                "business_unit": bu,
                "office_location": loc,
                "level": level,
            }

            r = db_update(TABLE_DIPENDENTI, f"email=eq.{email_pk}", payload)
            if r.status_code < 300:
                st.success("Dipendente aggiornato!")
            else:
                st.error(f"❌ Errore update: {r.text}")

    st.markdown("---")

    st.subheader("Elimina dipendente")
    if st.button("❌ Elimina questo dipendente"):
        r = db_delete(TABLE_DIPENDENTI, f"email=eq.{email_pk}")
        if r.status_code < 300:
            st.success("Dipendente eliminato!")
        else:
            st.error(f"❌ Errore delete: {r.text}")
