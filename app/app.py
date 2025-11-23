import streamlit as st
import requests
import pandas as pd
import io

st.set_page_config(page_title="HR Leave Management", layout="wide")

# Load secrets
SUPABASE_URL = st.secrets["SUPABASE_URL"]     # e.g. https://xxxx.supabase.co
API_KEY = st.secrets["SUPABASE_ANON_KEY"]

headers = {
    "apikey": API_KEY,
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# -------------------------------------------------------
# Utility: fetch table
# -------------------------------------------------------
def fetch_table(table):
    url = f"{SUPABASE_URL}/rest/v1/{table}?select=*"
    r = requests.get(url, headers=headers)

    if r.status_code == 200:
        try:
            return pd.DataFrame(r.json())
        except Exception:
            st.error("❌ Error parsing JSON response")
            return pd.DataFrame()
    else:
        st.error(f"❌ Error fetching {table}: {r.text}")
        return pd.DataFrame()


# -------------------------------------------------------
# Utility: DF → Excel / CSV / JSON bytes
# -------------------------------------------------------
def df_to_excel_bytes(df: pd.DataFrame) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

def df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")

def df_to_json_bytes(df: pd.DataFrame) -> bytes:
    # records array of objects [{...}, {...}]
    s = df.to_json(orient="records", force_ascii=False, date_format="iso")
    return s.encode("utf-8")


# -------------------------------------------------------
# UI LAYOUT
# -------------------------------------------------------
st.title("HR Leave Management Dashboard")

tab1, tab2 = st.tabs(["Dipendenti", "Richieste Ferie"])


# -------------------------------------------------------
# TAB 1 — DIPENDENTI
# -------------------------------------------------------
with tab1:
    st.header("Dipendenti")

    df = fetch_table("dipendenti")
    st.dataframe(df)

    # ------------------------
    # FORM: Add Dipendente
    # ------------------------
    st.subheader("Aggiungi Dipendente")
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

    # ------------------------
    # XLSX Upload → Insert
    # ------------------------
    st.subheader("Importa Dipendenti da Excel")

    uploaded_file = st.file_uploader("Carica file Excel (.xlsx)", type=["xlsx"])

    if uploaded_file:
        df_upload = pd.read_excel(uploaded_file)
        st.write("📄 Anteprima:")
        st.dataframe(df_upload)

        if st.button("Importa nel database"):
            successes = 0
            failures = []

            for _, row in df_upload.iterrows():
                payload = row.to_dict()

                r = requests.post(
                    f"{SUPABASE_URL}/rest/v1/dipendenti",
                    headers=headers,
                    json=payload
                )

                if r.status_code < 300:
                    successes += 1
                else:
                    failures.append({"row": row.to_dict(), "error": r.text})

            st.success(f"Import completato! {successes} righe inserite.")

            if failures:
                st.error("Alcune righe non sono state inserite:")
                st.json(failures)

    # ------------------------
    # Download Dipendenti
    # ------------------------
    st.subheader("Scarica tabella dipendenti")

    col_xlsx, col_csv, col_json = st.columns(3)

    with col_xlsx:
        st.download_button(
            "📥 Excel",
            data=df_to_excel_bytes(df),
            file_name="dipendenti.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    with col_csv:
        st.download_button(
            "📥 CSV",
            data=df_to_csv_bytes(df),
            file_name="dipendenti.csv",
            mime="text/csv",
        )

    with col_json:
        st.download_button(
            "📥 JSON",
            data=df_to_json_bytes(df),
            file_name="dipendenti.json",
            mime="application/json",
        )


# -------------------------------------------------------
# TAB 2 — RICHIESTE FERIE
# -------------------------------------------------------
with tab2:
    st.header("Richieste Ferie")

    df2 = fetch_table("richieste_ferie")
    st.dataframe(df2)

    # ------------------------
    # FORM: Add richiesta ferie
    # ------------------------
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

    # ------------------------
    # Download Richieste Ferie
    # ------------------------
    st.subheader("Scarica tabella richieste ferie")

    col2_xlsx, col2_csv, col2_json = st.columns(3)

    with col2_xlsx:
        st.download_button(
            "📥 Excel",
            data=df_to_excel_bytes(df2),
            file_name="richieste_ferie.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    with col2_csv:
        st.download_button(
            "📥 CSV",
            data=df_to_csv_bytes(df2),
            file_name="richieste_ferie.csv",
            mime="text/csv",
        )

    with col2_json:
        st.download_button(
            "📥 JSON",
            data=df_to_json_bytes(df2),
            file_name="richieste_ferie.json",
            mime="application/json",
        )
