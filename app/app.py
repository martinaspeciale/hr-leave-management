import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="HR Leave Management", layout="wide")

# Load secrets
SUPABASE_URL = st.secrets["SUPABASE_URL"]     # MUST NOT end with /rest/v1
API_KEY = st.secrets["SUPABASE_ANON_KEY"]

headers = {
    "apikey": API_KEY,
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# -----------------------
# Utility: fetch table
# -----------------------
def fetch_table(table):
    url = f"{SUPABASE_URL}/rest/v1/{table}?select=*"
    r = requests.get(url, headers=headers)

    # Debug info
    st.write(f"🔍 Request URL ({table}):", url)
    st.write(f"📡 Status Code:", r.status_code)
    st.write(f"📦 Raw Response:", r.text)

    if r.status_code == 200:
        try:
            return pd.DataFrame(r.json())
        except:
            st.error("❌ Error parsing JSON response")
            return pd.DataFrame()
    else:
        st.error(f"❌ Error fetching {table}: {r.text}")
        return pd.DataFrame()


# -----------------------
# UI
# -----------------------
st.title("HR Leave Management Dashboard")

tab1, tab2 = st.tabs(["Dipendenti", "Richieste Ferie"])


# -------------------------------------------------------
# TAB 1 — DIPENDENTI
# -------------------------------------------------------
with tab1:
    st.header("Dipendenti")

    df = fetch_table("dipendenti")
    st.dataframe(df)

    st.subheader("Aggiungi Dipendente")
    with st.form("add_dip"):
        email = st.text_input("Email")
        nome = st.text_input("Nome")
        cognome = st.text_input("Cognome")
        business_unit = st.text_input("Business Unit")
        office_location = st.text_input("Office Location")
        level = st.text_input("Level")
        submitted = st.form_submit_button("Add")

        if submitted:
            payload = {
                "email": email,
                "nome": nome,
                "cognome": cognome,
                "business_unit": business_unit,
                "office_location": office_location,
                "level": level
            }

            r = requests.post(
                f"{SUPABASE_URL}/rest/v1/dipendenti",
                headers=headers,
                json=payload,
            )

            if r.status_code < 300:
                st.success("Dipendente aggiunto!")
            else:
                st.error(f"❌ Insert error: {r.text}")


# -------------------------------------------------------
# TAB 2 — RICHIESTE FERIE
# -------------------------------------------------------
with tab2:
    st.header("Richieste Ferie")

    df2 = fetch_table("richieste_ferie")
    st.dataframe(df2)

    st.subheader("Nuova Richiesta Ferie")

    with st.form("add_req"):
        dip_email = st.text_input("Dipendente Email")
        data_inizio = st.date_input("Data Inizio")
        data_fine = st.date_input("Data Fine")
        motivo = st.text_input("Motivo")

        submitted2 = st.form_submit_button("Invia")

        if submitted2:
            delta = (data_fine - data_inizio).days + 1
            payload = {
                "dipendente_email": dip_email,
                "data_inizio": str(data_inizio),
                "data_fine": str(data_fine),
                "giorni_totali": delta,
                "motivo": motivo,
            }

            r = requests.post(
                f"{SUPABASE_URL}/rest/v1/richieste_ferie",
                headers=headers,
                json=payload,
            )

            if r.status_code < 300:
                st.success("Richiesta registrata!")
            else:
                st.error(f"❌ Insert error: {r.text}")
