import streamlit as st
import requests
import pandas as pd
import io

GREEN_PALETTE = [
    "#E8F5E9",  # very light green
    "#A5D6A7",  # light green
    "#66BB6A",  # medium green
    "#43A047",  # dark green
    "#1B5E20",  # very dark green
]

STATUS_PALETTE = [
    "#E6B8B9",  # soft antique rose
    "#D46A6A",  # warm medium red
    "#A63D40",  # dark wine red
    "#7B241C",  # deep bordeaux
]


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
    st.title("HR Leave Management Dashboard")

    # ------------------------------------------------------------------
    # FILTRI GLOBALI
    # ------------------------------------------------------------------
    with st.expander("Filtri avanzati", expanded=False):

        st.write("Puoi filtrare i dati del dashboard per Business Unit, livello, stato e periodo ferie.")

        f_col1, f_col2, f_col3 = st.columns(3)

        # Business Unit
        if df_dip is not None and not df_dip.empty and "business_unit" in df_dip.columns:
            bu_options = sorted(df_dip["business_unit"].dropna().unique())
        else:
            bu_options = []

        with f_col1:
            selected_bu = st.multiselect(
                "Business Unit",
                options=bu_options,
                default=bu_options,
            )

        # Level
        if df_dip is not None and not df_dip.empty and "level" in df_dip.columns:
            level_options = sorted(df_dip["level"].dropna().unique())
        else:
            level_options = []

        with f_col2:
            selected_levels = st.multiselect(
                "Level",
                options=level_options,
                default=level_options,
            )

        # Stato richiesta
        if df_req is not None and not df_req.empty and "status" in df_req.columns:
            status_options = sorted(df_req["status"].dropna().unique())
        else:
            status_options = []

        with f_col3:
            selected_status = st.multiselect(
                "Stato richiesta",
                options=status_options,
                default=status_options,
            )

        # Filtro periodo (data_inizio + data_fine)
        date_range = None
        if df_req is not None and not df_req.empty and "data_inizio" in df_req.columns:

            # Parse date_inizio / date_fine
            start_series = pd.to_datetime(df_req["data_inizio"], errors="coerce")
            if "data_fine" in df_req.columns:
                end_series = pd.to_datetime(
                    df_req["data_fine"].fillna(df_req["data_inizio"]),
                    errors="coerce",
                )
            else:
                end_series = start_series

            # Limiti min/max per default del date_input
            min_date = start_series.min().date()
            max_date = end_series.max().date()

            if pd.notna(min_date) and pd.notna(max_date):
                st.caption("Filtro periodo ferie (intervallo che si sovrappone al range selezionato)")
                date_range = st.date_input(
                    "Periodo",
                    value=(min_date, max_date),
                )


    # ------------------------------------------------------------------
    # APPLICAZIONE FILTRI
    # ------------------------------------------------------------------
    df_dip_filt = df_dip.copy() if df_dip is not None else pd.DataFrame()
    df_req_filt = df_req.copy() if df_req is not None else pd.DataFrame()

    # Filtri su dipendenti
    if not df_dip_filt.empty:
        if selected_bu:
            df_dip_filt = df_dip_filt[df_dip_filt["business_unit"].isin(selected_bu)]
        if selected_levels:
            df_dip_filt = df_dip_filt[df_dip_filt["level"].isin(selected_levels)]

    # Filtri su richieste
    if not df_req_filt.empty and "dipendente_email" in df_req_filt.columns:
        # Filtra per stato
        if selected_status:
            df_req_filt = df_req_filt[df_req_filt["status"].isin(selected_status)]

        # Collega alle persone filtrate
        if not df_dip_filt.empty and "email" in df_dip_filt.columns:
            df_req_filt = df_req_filt[
                df_req_filt["dipendente_email"].isin(df_dip_filt["email"])
            ]

        # Filtro periodo su [data_inizio, data_fine]
        if date_range and len(date_range) == 2 and "data_inizio" in df_req_filt.columns:
            start_date_sel, end_date_sel = date_range

            start_series = pd.to_datetime(df_req_filt["data_inizio"], errors="coerce")

            if "data_fine" in df_req_filt.columns:
                end_series = pd.to_datetime(
                    df_req_filt["data_fine"].fillna(df_req_filt["data_inizio"]),
                    errors="coerce",
                )
            else:
                end_series = start_series

            # Manteniamo le richieste il cui intervallo [inizio, fine]
            # SI SOVRAPPONE al range [start_date_sel, end_date_sel]
            mask = (
                (end_series.dt.date >= start_date_sel)
                & (start_series.dt.date <= end_date_sel)
            )
            df_req_filt = df_req_filt[mask]

    st.markdown("---")

    # ------------------------------------------------------------------
    # KPIs (basati sui dati filtrati)
    # ------------------------------------------------------------------
    num_dip = len(df_dip_filt) if df_dip_filt is not None else 0
    num_req = len(df_req_filt) if df_req_filt is not None else 0
    num_pending = 0
    if df_req_filt is not None and not df_req_filt.empty and "status" in df_req_filt.columns:
        num_pending = (df_req_filt["status"] == "PENDING").sum()

    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Dipendenti", num_dip)
    kpi2.metric("Richieste ferie", num_req)
    kpi3.metric("Richieste PENDING", int(num_pending))

    st.markdown("---")

    col_left, col_right = st.columns(2)

    # ------------------------------------------------------------------
    # SINISTRA: Dipendenti per BU (PIE VERDE)
    # ------------------------------------------------------------------
    with col_left:
        st.subheader("Dipendenti per Business Unit")

        if df_dip_filt is not None and not df_dip_filt.empty and "business_unit" in df_dip_filt.columns:
            df_bu = df_dip_filt.copy()
            df_bu["business_unit"] = (
                df_bu["business_unit"]
                .astype(str)
                .str.strip()
                .str.lower()
                .str.replace(r"\s+", " ", regex=True)
                .str.title()
            )

            bu_counts = (
                df_bu["business_unit"]
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
                color_discrete_sequence=GREEN_PALETTE,
            )

            fig.update_layout(
                showlegend=True,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="white",
            )

            st.plotly_chart(fig, use_container_width=True)

            # Totale dipendenti filtrati
            st.markdown(f"**Totale dipendenti:** {num_dip}")

            # Ultimo aggiornamento dati (basato su df_dip "pieno")
            if df_dip is not None and not df_dip.empty and "last_updated" in df_dip.columns:
                serie = pd.to_datetime(df_dip["last_updated"], errors="coerce", utc=True)
                serie_rome = serie.dt.tz_convert("Europe/Rome")
                last_upd = serie_rome.max()

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

    # ------------------------------------------------------------------
    # DESTRA: Richieste per stato (BAR BORDEAUX)
    # ------------------------------------------------------------------
    with col_right:
        st.subheader("Richieste ferie per stato")

        if df_req_filt is not None and not df_req_filt.empty and "status" in df_req_filt.columns:
            status_counts = (
                df_req_filt["status"]
                .value_counts()
                .rename_axis("status")
                .reset_index(name="count")
            )

            import plotly.express as px

            fig2 = px.bar(
                status_counts,
                x="status",
                y="count",
                title="Richieste per stato",
                text="count",
                color="status",
                color_discrete_sequence=STATUS_PALETTE,
            )

            fig2.update_layout(
                showlegend=False,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="white",
                yaxis=dict(
                    dtick=1,
                    tick0=0,
                    rangemode="tozero",
                    tickformat="d",
                ),
            )

            fig2.update_traces(
                textposition="outside",
                cliponaxis=False,
            )

            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Nessun dato sulle richieste o colonna status mancante.")

    st.markdown("---")

    # ------------------------------------------------------------------
    # GRAFICO EXTRA: Giorni di ferie per mese
    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # GRAFICO: Andamento giornaliero delle ferie (line chart)
    # ------------------------------------------------------------------
    st.subheader("Andamento giornaliero delle ferie")

    if df_req_filt is not None and not df_req_filt.empty and "data_inizio" in df_req_filt.columns:
        df_daily = df_req_filt.copy()

        # Parse date_inizio / date_fine
        df_daily["data_inizio"] = pd.to_datetime(df_daily["data_inizio"], errors="coerce")

        if "data_fine" in df_daily.columns:
            df_daily["data_fine"] = pd.to_datetime(
                df_daily["data_fine"].fillna(df_daily["data_inizio"]),
                errors="coerce",
            )
        else:
            df_daily["data_fine"] = df_daily["data_inizio"]

        # Rimuoviamo righe senza date valide
        df_daily = df_daily.dropna(subset=["data_inizio", "data_fine"])

        # Ci assicuriamo che inizio <= fine
        df_daily.loc[df_daily["data_fine"] < df_daily["data_inizio"], ["data_inizio", "data_fine"]] = \
            df_daily.loc[df_daily["data_fine"] < df_daily["data_inizio"], ["data_fine", "data_inizio"]].values

        if not df_daily.empty:
            # Generiamo un elenco di giorni per ogni richiesta (range inclusivo)
            df_daily["giorni_range"] = df_daily.apply(
                lambda r: pd.date_range(r["data_inizio"].date(), r["data_fine"].date(), freq="D"),
                axis=1,
            )
            df_expanded = df_daily.explode("giorni_range")

            # Contiamo quante richieste sono attive per ciascun giorno
            ferie_per_giorno = (
                df_expanded.groupby("giorni_range")
                .size()
                .reset_index(name="num_richieste")
                .sort_values("giorni_range")
            )

            import plotly.express as px

            fig3 = px.line(
                ferie_per_giorno,
                x="giorni_range",
                y="num_richieste",
                title="Numero di richieste di ferie attive per giorno",
            )

            fig3.update_traces(mode="lines+markers")

            fig3.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="white",
                xaxis=dict(
                    title="Giorni",
                    showgrid=False,
                ),
                yaxis=dict(
                    title="Numero richieste ferie",
                    dtick=1,
                    tick0=0,
                    rangemode="tozero",
                    tickformat="d",
                ),
            )

            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.caption("Nessuna data valida per costruire l'andamento giornaliero.")
    else:
        st.caption("Nessun dato `data_inizio` disponibile per l'andamento giornaliero.")


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

        fmt = st.radio(
            "Formato file",
            ["Excel (.xlsx)", "CSV (.csv)", "JSON (.json)"],
            horizontal=True,
        )

        if fmt == "Excel (.xlsx)":
            data = df_to_excel_bytes(df_dip)
            file_name = "dipendenti.xlsx"
            mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif fmt == "CSV (.csv)":
            data = df_to_csv_bytes(df_dip)
            file_name = "dipendenti.csv"
            mime = "text/csv"
        else:  # JSON
            data = df_to_json_bytes(df_dip)
            file_name = "dipendenti.json"
            mime = "application/json"

        st.download_button(
            "📥 Scarica",
            data=data,
            file_name=file_name,
            mime=mime,
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

    elif action == "Import":
        st.subheader("Importa dipendenti da file")

        uploaded_file = st.file_uploader(
            "Carica file (.xlsx o .csv)",
            type=["xlsx", "csv"],
        )

        if uploaded_file:
            filename = uploaded_file.name.lower()

            # Lettura CSV/Excel
            if filename.endswith(".csv"):
                df_upload = pd.read_csv(uploaded_file)
            else:
                df_upload = pd.read_excel(uploaded_file)

            # 🔥 SANIFICAZIONE COMPLETA 🔥
            df_upload = df_upload.replace({pd.NA: None, "None": None, "nan": None})
            df_upload = df_upload.where(pd.notnull(df_upload), None)

            # Rimuovere colonne che non vanno mostrate 
            df_preview = df_upload.drop(columns=["last_updated"], errors="ignore")

            st.write("📄 Anteprima file:")
            st.dataframe(df_preview)


            if st.button("Importa nel database"):
                successes = 0
                failures = []

                for _, row in df_upload.iterrows():

                    # Conversione row → dict con pulizia JSON-safe
                    payload = {}
                    for k, v in row.to_dict().items():
                        if pd.isna(v) or v in ["None", "nan", "NaN", ""]:
                            payload[k] = None
                        else:
                            payload[k] = v
                    
                    payload.pop("last_updated", None)


                    # POST verso Supabase
                    r = requests.post(
                        f"{SUPABASE_URL}/rest/v1/dipendenti",
                        headers=get_auth_headers(),
                        json=payload,
                    )

                    if r.status_code < 300:
                        successes += 1
                    else:
                        failures.append({"row": payload, "error": r.text})

                # Output
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

        fmt = st.radio(
            "Formato file",
            ["Excel (.xlsx)", "CSV (.csv)", "JSON (.json)"],
            horizontal=True,
        )

        if fmt == "Excel (.xlsx)":
            data = df_to_excel_bytes(df_req)
            file_name = "richieste_ferie.xlsx"
            mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif fmt == "CSV (.csv)":
            data = df_to_csv_bytes(df_req)
            file_name = "richieste_ferie.csv"
            mime = "text/csv"
        else:
            data = df_to_json_bytes(df_req)
            file_name = "richieste_ferie.json"
            mime = "application/json"

        st.download_button(
            "📥 Scarica",
            data=data,
            file_name=file_name,
            mime=mime,
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
            ["Vista & download", "Aggiungi singolo", "Import", "Modifica / Elimina"],
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

