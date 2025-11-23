import streamlit as st
import requests
import pandas as pd
import io

st.set_page_config(page_title="HR Leave Management", layout="wide")

# ---------------------------------------
# Secrets / Config
# ---------------------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]     # e.g. https://xxxx.supabase.co
API_KEY = st.secrets["SUPABASE_ANON_KEY"]     # publishable key


# ---------------------------------------
# Auth helpers
# ---------------------------------------
def get_auth_headers() -> dict | None:
    """Headers per chiamate REST autenticate con Supabase Auth JWT."""
    token = st.session_state.get("access_token")
    if not token:
        return None
    return {
        "apikey": API_KEY,
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def login(email: str, password: str) -> bool:
    """Esegue login contro Supabase Auth (email/password)."""
    url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
    headers = {
        "apikey": API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "email": email,
        "password": password,
    }
    r = requests.post(url, headers=headers, json=payload)
    if r.status_code == 200:
        data = r.json()
        st.session_state["access_token"] = data["access_token"]
        user = data.get("user", {})
        st.session_state["user_email"] = user.get("email", email)
        return True
    else:
        st.error(f"❌ Login fallito: {r.text}")
        return False


def logout():
    st.session_state.pop("access_token", None)
    st.session_state.pop("user_email", None)


# ---------------------------------------
# Utilities
# ---------------------------------------
def fetch_table(table: str) -> pd.DataFrame:
    headers = get_auth_headers()
    if not headers:
        return pd.DataFrame()

    url = f"{SUPABASE_URL}/rest/v1/{table}?select=*"
    r = requests.get(url, headers=headers)

    if r.status_code == 200:
        try:
            return pd.DataFrame(r.json())
        except Exception:
            st.error(f"❌ Error parsing JSON for table {table}")
            return pd.DataFrame()
    else:
        st.error(f"❌ Error fetching {table}: {r.text}")
        return pd.DataFrame()


def df_to_excel_bytes(df: pd.DataFrame) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()


def df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def df_to_json_bytes(df: pd.DataFrame) -> bytes:
    s = df.to_json(orient="records", force_ascii=False, date_format="iso")
    return s.encode("utf-8")


# ---------------------------------------
# Page: Home (Dashboard)
# ---------------------------------------
def render_home(df_dip: pd.DataFrame, df_req: pd.DataFrame):
    st.title("HR Leave Management – Dashboard")

    col1, col2, col3 = st.columns(3)

    num_dip = len(df_dip) if not df_dip.empty else 0
    num_req = len(df_req) if not df_req.empty else 0
    if not df_req.empty and "status" in df_req.columns:
        num_pending = (df_req["status"] == "PENDING").sum()
    else:
        num_pending = 0

    col1.metric("Dipendenti totali", num_dip)
    col2.metric("Richieste ferie totali", num_req)
    col3.metric("Richieste in sospeso", num_pending)

    st.markdown("---")

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Dipendenti per Business Unit")

        if not df_dip.empty and "business_unit" in df_dip.columns:

            # Normalizzazione Business Unit
            df_dip["business_unit"] = (
                df_dip["business_unit"]
                .astype(str)
                .str.strip()
                .str.lower()
                .str.replace(r"\s+", " ", regex=True)
                .str.title()
            )

            bu_counts = (
                df_dip["business_unit"]
                .value_counts()
                .rename_axis("business_unit")
                .reset_index(name="count")
            )

            import plotly.express as px

            fig = px.pie(
                bu_counts,
                names="business_unit",
                values="count",
                title="Distribuzione Dipendenti per Business Unit",
                color_discrete_sequence=px.colors.qualitative.Pastel
            )

            fig.update_layout(
                showlegend=True,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="white"
            )

            st.plotly_chart(fig, use_container_width=True)

            # 👇 RIEPILOGO SOTTO IL GRAFICO

            # Totale dipendenti (usa num_dip definito sopra in render_home)
            st.markdown(f"**Totale dipendenti nel DB:** {num_dip}")

            # Ultimo aggiornamento (colonna last_updated)
            if "last_updated" in df_dip.columns:
                last_upd = pd.to_datetime(df_dip["last_updated"], errors="coerce").max()
                if pd.notna(last_upd):
                    st.markdown(
                        f"**Ultimo aggiornamento dati:** {last_upd.strftime('%d/%m/%Y %H:%M')}"
                    )
                else:
                    st.caption("Ultimo aggiornamento: non disponibile.")
            else:
                st.caption("Colonna `last_updated` non presente nella tabella.")

        else:
            st.info("Nessun dato sui dipendenti o colonna business_unit mancante.")


    with col_right:
        st.subheader("Richieste ferie per stato")
        if not df_req.empty and "status" in df_req.columns:
            status_counts = (
                df_req["status"]
                .value_counts()
                .rename_axis("status")
                .reset_index(name="count")
            )
            st.bar_chart(status_counts.set_index("status"))
        else:
            st.info("Nessun dato sulle richieste o colonna status mancante.")

    st.markdown("---")
    st.caption("Usa il menu a sinistra per gestire dipendenti e richieste ferie.")


# ---------------------------------------
# Page: Dipendenti
# ---------------------------------------
def render_dipendenti(df_dip: pd.DataFrame, action: str):
    st.title("Gestione Dipendenti")

    headers = get_auth_headers()
    if not headers:
        st.error("Non sei autenticatə.")
        return

    if df_dip is None:
        df_dip = pd.DataFrame()

    if action == "Vista & download":
        st.subheader("Elenco dipendenti")
        st.dataframe(df_dip)

        st.subheader("Scarica tabella dipendenti")

        col_xlsx, col_csv, col_json = st.columns(3)

        with col_xlsx:
            st.download_button(
                "📥 Excel",
                data=df_to_excel_bytes(df_dip),
                file_name="dipendenti.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        with col_csv:
            st.download_button(
                "📥 CSV",
                data=df_to_csv_bytes(df_dip),
                file_name="dipendenti.csv",
                mime="text/csv",
            )

        with col_json:
            st.download_button(
                "📥 JSON",
                data=df_to_json_bytes(df_dip),
                file_name="dipendenti.json",
                mime="application/json",
            )

    elif action == "Aggiungi singolo":
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
                    st.error(f"❌ Errore inserimento: {r.text}")

    elif action == "Import da Excel":
        st.subheader("Importa dipendenti da file Excel")

        uploaded_file = st.file_uploader("Carica file Excel (.xlsx)", type=["xlsx"])

        if uploaded_file:
            df_upload = pd.read_excel(uploaded_file)
            st.write("📄 Anteprima file:")
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

    elif action == "Modifica / Elimina":
        st.subheader("Modifica o elimina dipendente")

        if df_dip.empty:
            st.info("Nessun dipendente presente.")
            return

        df_dip = df_dip.copy()
        df_dip["label"] = df_dip.apply(
            lambda r: f"{r.get('nome','')} {r.get('cognome','')} ({r.get('email','')})",
            axis=1,
        )

        selected_label = st.selectbox(
            "Seleziona dipendente",
            df_dip["label"].tolist(),
        )

        selected_row = df_dip[df_dip["label"] == selected_label].iloc[0]
        email_pk = selected_row["email"]

        st.write("📌 Modifica dati:")

        with st.form("edit_dip"):
            nome = st.text_input("Nome", value=selected_row.get("nome", ""))
            cognome = st.text_input("Cognome", value=selected_row.get("cognome", ""))
            business_unit = st.text_input("Business Unit", value=selected_row.get("business_unit", ""))
            office_location = st.text_input("Office Location", value=selected_row.get("office_location", ""))
            level = st.text_input("Level", value=selected_row.get("level", ""))
            submitted_update = st.form_submit_button("Salva modifiche")

            if submitted_update:
                payload = {
                    "nome": nome,
                    "cognome": cognome,
                    "business_unit": business_unit,
                    "office_location": office_location,
                    "level": level,
                }
                url = f"{SUPABASE_URL}/rest/v1/dipendenti?email=eq.{email_pk}"
                r = requests.patch(url, headers=headers, json=payload)
                if r.status_code < 300:
                    st.success("Dipendente aggiornato!")
                else:
                    st.error(f"❌ Errore update: {r.text}")

        st.markdown("---")
        st.subheader("Elimina dipendente")

        if st.button("❌ Elimina questo dipendente"):
            url = f"{SUPABASE_URL}/rest/v1/dipendenti?email=eq.{email_pk}"
            r = requests.delete(url, headers=headers)
            if r.status_code < 300:
                st.success("Dipendente eliminato!")
            else:
                st.error(f"❌ Errore delete: {r.text}")


# ---------------------------------------
# Page: Richieste Ferie
# ---------------------------------------
def render_richieste(df_req: pd.DataFrame, action: str):
    st.title("Gestione Richieste Ferie")

    headers = get_auth_headers()
    if not headers:
        st.error("Non sei autenticatə.")
        return

    if df_req is None:
        df_req = pd.DataFrame()

    if action == "Vista & download":
        st.subheader("Elenco richieste ferie")
        st.dataframe(df_req)

        st.subheader("Scarica tabella richieste ferie")

        col_xlsx, col_csv, col_json = st.columns(3)

        with col_xlsx:
            st.download_button(
                "📥 Excel",
                data=df_to_excel_bytes(df_req),
                file_name="richieste_ferie.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        with col_csv:
            st.download_button(
                "📥 CSV",
                data=df_to_csv_bytes(df_req),
                file_name="richieste_ferie.csv",
                mime="text/csv",
            )

        with col_json:
            st.download_button(
                "📥 JSON",
                data=df_to_json_bytes(df_req),
                file_name="richieste_ferie.json",
                mime="application/json",
            )

    elif action == "Nuova richiesta":
        st.subheader("Registra una nuova richiesta ferie")

        with st.form("add_req"):
            dip_email = st.text_input("Dipendente Email")
            data_inizio = st.date_input("Data inizio")
            data_fine = st.date_input("Data fine")
            motivo = st.text_input("Motivo")

            submitted2 = st.form_submit_button("Invia richiesta")

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
                    st.error(f"❌ Errore inserimento: {r.text}")

    elif action == "Modifica / Elimina":
        st.subheader("Modifica o elimina richiesta ferie")

        if df_req.empty:
            st.info("Nessuna richiesta presente.")
            return

        if "id" not in df_req.columns:
            st.error("La tabella richieste_ferie non ha una colonna 'id'.")
            return

        df_req = df_req.copy()
        df_req["label"] = df_req.apply(
            lambda r: f"ID {r['id']} – {r.get('dipendente_email','')} ({r.get('status','')})",
            axis=1,
        )

        selected_label = st.selectbox(
            "Seleziona richiesta",
            df_req["label"].tolist(),
        )

        selected_row = df_req[df_req["label"] == selected_label].iloc[0]
        req_id = selected_row["id"]

        with st.form("edit_req"):
            dip_email = st.text_input("Dipendente Email", value=selected_row.get("dipendente_email", ""))
            data_inizio = st.date_input(
                "Data inizio",
                value=pd.to_datetime(selected_row.get("data_inizio")).date(),
            )
            data_fine = st.date_input(
                "Data fine",
                value=pd.to_datetime(selected_row.get("data_fine")).date(),
            )
            motivo = st.text_input("Motivo", value=selected_row.get("motivo", "") or "")
            status = st.selectbox(
                "Status",
                options=["PENDING", "APPROVED", "REJECTED", "CANCELLED"],
                index=["PENDING", "APPROVED", "REJECTED", "CANCELLED"].index(
                    selected_row.get("status", "PENDING")
                )
                if selected_row.get("status") in ["PENDING", "APPROVED", "REJECTED", "CANCELLED"]
                else 0,
            )

            submitted_update = st.form_submit_button("Salva modifiche")

            if submitted_update:
                delta = (data_fine - data_inizio).days + 1
                payload = {
                    "dipendente_email": dip_email,
                    "data_inizio": str(data_inizio),
                    "data_fine": str(data_fine),
                    "giorni_totali": delta,
                    "motivo": motivo,
                    "status": status,
                }
                url = f"{SUPABASE_URL}/rest/v1/richieste_ferie?id=eq.{req_id}"
                r = requests.patch(url, headers=headers, json=payload)
                if r.status_code < 300:
                    st.success("Richiesta aggiornata!")
                else:
                    st.error(f"❌ Errore update: {r.text}")

        st.markdown("---")
        st.subheader("Elimina richiesta")

        if st.button("❌ Elimina questa richiesta"):
            url = f"{SUPABASE_URL}/rest/v1/richieste_ferie?id=eq.{req_id}"
            r = requests.delete(url, headers=headers)
            if r.status_code < 300:
                st.success("Richiesta eliminata!")
            else:
                st.error(f"❌ Errore delete: {r.text}")


# ---------------------------------------
# MAIN APP (with login gate)
# ---------------------------------------
def main_app():
    st.sidebar.title("Menu")

    st.sidebar.write(f"👤 {st.session_state.get('user_email', '')}")
    if st.sidebar.button("Logout"):
        logout()
        st.rerun()


    section = st.sidebar.radio(
        "Seleziona sezione",
        ["Home", "Dipendenti", "Richieste ferie"],
    )

    dip_action = None
    req_action = None

    if section == "Dipendenti":
        st.sidebar.markdown("### Azioni dipendenti")
        dip_action = st.sidebar.radio(
            "Seleziona azione",
            ["Vista & download", "Aggiungi singolo", "Import da Excel", "Modifica / Elimina"],
            index=0,
        )

    if section == "Richieste ferie":
        st.sidebar.markdown("### Azioni richieste ferie")
        req_action = st.sidebar.radio(
            "Seleziona azione",
            ["Vista & download", "Nuova richiesta", "Modifica / Elimina"],
            index=0,
        )

    df_dip = fetch_table("dipendenti")
    df_req = fetch_table("richieste_ferie")

    if section == "Home":
        render_home(df_dip, df_req)
    elif section == "Dipendenti":
        render_dipendenti(df_dip, dip_action)
    elif section == "Richieste ferie":
        render_richieste(df_req, req_action)


def main():
    # se non autenticatə, mostra login
    if "access_token" not in st.session_state:
        st.title("HR Leave Management – Login")

        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")

            if submitted:
                ok = login(email, password)
                if ok:
                    st.rerun()

        st.stop()
    else:
        main_app()


if __name__ == "__main__":
    main()
