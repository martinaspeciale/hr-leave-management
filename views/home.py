# pages/home.py

"""
Home dashboard page with filters, KPIs, and charts.
"""

import streamlit as st
import pandas as pd
import calendar
from datetime import date

from utils.db import fetch_table
from views.charts import (
    chart_dipendenti_per_bu,
    chart_richieste_per_status,
    chart_andamento_ferie,
)


def render_home(df_dip, df_req):
    st.title("HR Leave Management Dashboard")

    # ---------------------------------------------------
    # FILTERS
    # ---------------------------------------------------
    with st.expander("Filtri avanzati", expanded=False):
        st.write("Filtra dati per Business Unit, livello, stato e periodo ferie.")

        col1, col2, col3 = st.columns(3)

        # Business Unit
        bu_options = (
            sorted(df_dip["business_unit"].dropna().unique())
            if not df_dip.empty else []
        )
        with col1:
            selected_bu = st.multiselect(
                "Business Unit",
                options=bu_options,
                default=bu_options,
            )

        # Level
        level_options = (
            sorted(df_dip["level"].dropna().unique())
            if not df_dip.empty else []
        )
        with col2:
            selected_levels = st.multiselect(
                "Level",
                options=level_options,
                default=level_options,
            )

        # Request status
        status_options = (
            sorted(df_req["status"].dropna().unique())
            if not df_req.empty else []
        )
        with col3:
            selected_status = st.multiselect(
                "Stato richiesta",
                options=status_options,
                default=status_options,
            )

        # Date range filter
        date_range = None
        if not df_req.empty:
            start_series = pd.to_datetime(df_req["data_inizio"], errors="coerce")
            end_series = pd.to_datetime(
                df_req["data_fine"].fillna(df_req["data_inizio"]),
                errors="coerce",
            )
            min_date = start_series.min().date()
            max_date = end_series.max().date()

            st.caption("Filtro periodo ferie (intervallo che si sovrappone al range selezionato)")
            date_range = st.date_input("Periodo", value=(min_date, max_date))

    # ---------------------------------------------------
    # APPLY FILTERS
    # ---------------------------------------------------
    df_dip_f = df_dip.copy()
    df_req_f = df_req.copy()

    if selected_bu:
        df_dip_f = df_dip_f[df_dip_f["business_unit"].isin(selected_bu)]

    if selected_levels:
        df_dip_f = df_dip_f[df_dip_f["level"].isin(selected_levels)]

    if selected_status:
        df_req_f = df_req_f[df_req_f["status"].isin(selected_status)]

    if not df_dip_f.empty:
        df_req_f = df_req_f[df_req_f["dipendente_email"].isin(df_dip_f["email"])]

    if date_range:
        start_sel, end_sel = date_range

        starts = pd.to_datetime(df_req_f["data_inizio"], errors="coerce")
        ends = pd.to_datetime(
            df_req_f["data_fine"].fillna(df_req_f["data_inizio"]),
            errors="coerce",
        )

        mask = (ends.dt.date >= start_sel) & (starts.dt.date <= end_sel)
        df_req_f = df_req_f[mask]

    st.markdown("---")

    # ---------------------------------------------------
    # KPIs
    # ---------------------------------------------------
    k1, k2, k3 = st.columns(3)
    k1.metric("Dipendenti", len(df_dip_f))
    k2.metric("Richieste ferie", len(df_req_f))
    k3.metric(
        "Richieste Pending",
        int((df_req_f["status"] == "PENDING").sum()) if not df_req_f.empty else 0,
    )

    st.markdown("---")

    # -------------------------------------------------------------
    # ANALISI MENSILE – Giorni di ferie richiesti per mese (working days only)
    # -------------------------------------------------------------
    def giorni_ferie_in_mese(df: pd.DataFrame, anno: int, mese: int) -> int:
        """
        Calcola solo i giorni lavorativi richiesti nel mese/anno selezionato.
        Usa la stessa logica del sistema: weekend esclusi, festività escluse.
        """

        from utils.calculations import is_working_day

        if df is None or df.empty:
            return 0

        df_local = df.copy()
        df_local["data_inizio"] = pd.to_datetime(df_local["data_inizio"], errors="coerce")
        df_local["data_fine"] = pd.to_datetime(df_local["data_fine"], errors="coerce")
        df_local = df_local.dropna(subset=["data_inizio", "data_fine"])

        # Fix swapped interval
        mask_swap = df_local["data_fine"] < df_local["data_inizio"]
        df_local.loc[mask_swap, ["data_inizio", "data_fine"]] = df_local.loc[
            mask_swap, ["data_fine", "data_inizio"]
        ].values

        if df_local.empty:
            return 0

        # Selected month boundaries
        month_start = date(anno, mese, 1)
        if mese == 12:
            month_end = date(anno, 12, 31)
        else:
            month_end = (pd.Timestamp(anno, mese + 1, 1) - pd.Timedelta(days=1)).date()

        total = 0

        for _, row in df_local.iterrows():
            start = row["data_inizio"].date()
            end = row["data_fine"].date()

            # Overlap
            s = max(start, month_start)
            e = min(end, month_end)
            if e < s:
                continue

            # Iterate
            days = pd.date_range(s, e, freq="D")

            working_days = [d for d in days if is_working_day(d.date())]
            total += len(working_days)

        return total

    st.markdown("### Analisi mensile ferie")

    col_anno, col_mese, col_metric = st.columns([1, 1, 2])

    with col_anno:
        anno_sel = st.selectbox("Anno", [2025, 2026], key="mese_anno_sel")

    with col_mese:
        mesi = list(range(1, 13))
        mese_sel = st.selectbox(
            "Mese",
            mesi,
            format_func=lambda m: calendar.month_name[m].capitalize(),
            key="mese_sel"
        )

    giorni_mese = giorni_ferie_in_mese(df_req_f, anno_sel, mese_sel)

    with col_metric:
        st.metric(
            label=f"Giorni lavorativi richiesti in {calendar.month_name[mese_sel].capitalize()} {anno_sel}",
            value=giorni_mese,
        )

    st.markdown("---")

    # ---------------------------------------------------
    # Charts
    # ---------------------------------------------------
    col_l, col_r = st.columns(2)

    with col_l:
        st.subheader("Dipendenti per Business Unit")
        fig_bu = chart_dipendenti_per_bu(df_dip_f)
        if fig_bu:
            st.plotly_chart(fig_bu, use_container_width=True)

    with col_r:
        st.subheader("Richieste ferie per stato")
        fig_stat = chart_richieste_per_status(df_req_f)
        if fig_stat:
            st.plotly_chart(fig_stat, use_container_width=True)

    st.markdown("---")

    st.subheader("Andamento giornaliero delle ferie")
    fig_daily = chart_andamento_ferie(df_req_f, selected_range=date_range)
    if fig_daily:
        st.plotly_chart(fig_daily, use_container_width=True)
