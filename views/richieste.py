# views/richieste.py

"""
Page: Gestione Richieste Ferie
CRUD operations for 'richieste_ferie'.
Applies new schema: giorni_lavorativi_2025 / giorni_lavorativi_2026.
"""

import streamlit as st
import pandas as pd

from utils.db import db_insert, db_update, db_delete
from utils.exports import (
    df_to_excel_bytes, df_to_csv_bytes, df_to_json_bytes
)
from utils.calculations import calcola_giorni_2025_2026
from settings.constants import TABLE_RICHIESTE


# -------------------------------------------------------------
# PAGE DISPATCHER
# -------------------------------------------------------------
def render_richieste(df_req: pd.DataFrame, action: str):
    st.title("Gestione Richieste Ferie")

    if df_req is None:
        df_req = pd.DataFrame()

    if action == "Vista & download":
        _page_vista(df_req)

    elif action == "Nuova richiesta":
        _page_add()

    elif action == "Modifica / Elimina":
        _page_edit_delete(df_req)


def _page_vista(df):
    st.subheader("Elenco richieste ferie")

    if df is None or df.empty:
        st.info("Nessuna richiesta presente.")
        return

    df_view = df.copy()

    # Nascondere colonne non rilevanti
    df_view = df_view.drop(
        columns=["motivo", "note", "data_richiesta"],
        errors="ignore"
    )

    # ---------------------------------------------------
    # 🔥 FORZARE ORDINE COLONNE
    # ---------------------------------------------------
    desired_order = [
        "id",
        "dipendente_email",
        "data_inizio",
        "data_fine",
        "giorni_lavorativi_2025",
        "giorni_lavorativi_2026",
        "status",
        "approvato_da",
        "created_date",
    ]

    # Tieni solo quelle effettivamente presenti
    ordered_cols = [c for c in desired_order if c in df_view.columns]
    other_cols = [c for c in df_view.columns if c not in ordered_cols]

    df_view = df_view[ordered_cols + other_cols]

    # ---------------------------------------------------
    # Rimozione underscore
    # ---------------------------------------------------
    df_view.columns = [col.replace("_", " ").title() for col in df_view.columns]

    st.dataframe(df_view, use_container_width=True)

    # ---------------------------------------------------
    # Download
    # ---------------------------------------------------
    st.subheader("Scarica tabella richieste ferie")

    fmt = st.radio(
        "Formato file",
        ["Excel (.xlsx)", "CSV (.csv)", "JSON (.json)"],
        horizontal=True,
    )

    if fmt == "Excel (.xlsx)":
        data = df_to_excel_bytes(df_view)
        fname = "richieste_ferie.xlsx"
        mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif fmt == "CSV (.csv)":
        data = df_to_csv_bytes(df_view)
        fname = "richieste_ferie.csv"
        mime = "text/csv"
    else:
        data = df_to_json_bytes(df_view)
        fname = "richieste_ferie.json"
        mime = "application/json"

    st.download_button("📥 Scarica", data=data, file_name=fname, mime=mime)


# -------------------------------------------------------------
# NUOVA RICHIESTA
# -------------------------------------------------------------
def _page_add():
    st.subheader("Registra una nuova richiesta ferie")

    with st.form("add_req"):
        email = st.text_input("Dipendente email")
        data_inizio = st.date_input("Data inizio")
        data_fine = st.date_input("Data fine")
        motivo = st.text_text_input("Motivo")

        submitted = st.form_submit_button("Invia richiesta")

        if submitted:
            g2025, g2026 = calcola_giorni_2025_2026(data_inizio, data_fine)

            payload = {
                "dipendente_email": email,
                "data_inizio": str(data_inizio),
                "data_fine": str(data_fine),
                "motivo": motivo,
                "giorni_lavorativi_2025": g2025,
                "giorni_lavorativi_2026": g2026,
            }

            r = db_insert(TABLE_RICHIESTE, payload)

            if r.status_code < 300:
                st.success("Richiesta registrata!")
            else:
                st.error(f"❌ Errore inserimento: {r.text}")


# -------------------------------------------------------------
# MODIFICA / ELIMINA RICHIESTA
# -------------------------------------------------------------
def _page_edit_delete(df):
    st.subheader("Modifica o elimina richiesta ferie")

    if df.empty:
        st.info("Nessuna richiesta presente.")
        return

    if "id" not in df.columns:
        st.error("La tabella richieste_ferie non ha colonna 'id'.")
        return

    df = df.copy()
    df["label"] = df.apply(
        lambda r: f"ID {r['id']} – {r.get('dipendente_email', '')} ({r.get('status', '')})",
        axis=1,
    )

    selected = st.selectbox("Seleziona richiesta", df["label"])
    row = df[df["label"] == selected].iloc[0]
    req_id = row["id"]

    with st.form("edit_req"):
        email = st.text_input("Dipendente email", value=row.get("dipendente_email", ""))

        data_inizio = st.date_input(
            "Data inizio",
            value=pd.to_datetime(row["data_inizio"]).date()
        )

        data_fine = st.date_input(
            "Data fine",
            value=pd.to_datetime(row["data_fine"]).date()
        )

        motivo = st.text_input("Motivo", value=row.get("motivo", "") or "")

        # NEW: campo note
        note = st.text_area("Note", value=row.get("note", "") or "")

        status = st.selectbox(
            "Status",
            ["PENDING", "APPROVED", "REJECTED", "CANCELLED"],
            index=["PENDING", "APPROVED", "REJECTED", "CANCELLED"].index(
                row.get("status", "PENDING")
            ),
        )

        submitted = st.form_submit_button("Salva modifiche")

        if submitted:
            g2025, g2026 = calcola_giorni_2025_2026(data_inizio, data_fine)

            payload = {
                "dipendente_email": email,
                "data_inizio": str(data_inizio),
                "data_fine": str(data_fine),
                "motivo": motivo,
                "note": note,
                "status": status,
                "giorni_lavorativi_2025": g2025,
                "giorni_lavorativi_2026": g2026,
            }

            r = db_update(TABLE_RICHIESTE, f"id=eq.{req_id}", payload)
            if r.status_code < 300:
                st.success("Richiesta aggiornata!")
            else:
                st.error(f"❌ Errore update: {r.text}")

    st.markdown("---")

    st.subheader("Elimina richiesta")
    if st.button("❌ Elimina questa richiesta"):
        r = db_delete(TABLE_RICHIESTE, f"id=eq.{req_id}")
        if r.status_code < 300:
            st.success("Richiesta eliminata!")
        else:
            st.error(f"❌ Errore delete: {r.text}")
