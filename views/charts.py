# pages/charts.py

"""
Chart rendering utilities used across the application.
All charts are extracted into reusable functions.
"""

import datetime
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from settings.palettes import GREEN_PALETTE, STATUS_PALETTE
from settings.constants import HOLIDAYS_FIXED


# --------------------------------------------------------
# PIE CHART: Employee distribution per Business Unit
# --------------------------------------------------------
def chart_dipendenti_per_bu(df):
    if df.empty or "business_unit" not in df.columns:
        return None

    df_clean = df.copy()
    df_clean["business_unit"] = (
        df_clean["business_unit"]
        .astype(str)
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", " ", regex=True)
        .str.title()
    )

    counts = (
        df_clean["business_unit"]
        .value_counts()
        .rename_axis("business_unit")
        .reset_index(name="count")
    )

    fig = px.pie(
        counts,
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

    return fig


# --------------------------------------------------------
# BAR CHART: Vacation requests per status
# --------------------------------------------------------
def chart_richieste_per_status(df):
    if df.empty or "status" not in df.columns:
        return None

    counts = (
        df["status"]
        .value_counts()
        .rename_axis("status")
        .reset_index(name="count")
    )

    fig = px.bar(
        counts,
        x="status",
        y="count",
        text="count",
        title="Richieste per stato",
        color="status",
        color_discrete_sequence=STATUS_PALETTE,
    )

    fig.update_layout(
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="white",
        yaxis=dict(dtick=1, tick0=0, rangemode="tozero"),
    )

    fig.update_traces(textposition="outside", cliponaxis=False)
    return fig


# --------------------------------------------------------
# LINE CHART: Daily active vacation requests
# --------------------------------------------------------
def chart_andamento_ferie(df, selected_range=None):
    if df.empty or "data_inizio" not in df.columns:
        return None

    df_daily = df.copy()
    df_daily["data_inizio"] = pd.to_datetime(df_daily["data_inizio"], errors="coerce")
    df_daily["data_fine"] = pd.to_datetime(
        df_daily.get("data_fine", df_daily["data_inizio"]), errors="coerce"
    )

    df_daily = df_daily.dropna(subset=["data_inizio", "data_fine"])

    # Ensure start <= end
    mask_swap = df_daily["data_fine"] < df_daily["data_inizio"]
    df_daily.loc[mask_swap, ["data_inizio", "data_fine"]] = df_daily.loc[
        mask_swap, ["data_fine", "data_inizio"]
    ].values

    if df_daily.empty:
        return None

    df_daily["giorni_range"] = df_daily.apply(
        lambda r: pd.date_range(r["data_inizio"].date(), r["data_fine"].date(), freq="D"),
        axis=1,
    )

    df_expanded = df_daily.explode("giorni_range")

    ferie_per_giorno = (
        df_expanded.groupby("giorni_range")
        .size()
        .reset_index(name="num_richieste")
        .sort_values("giorni_range")
    )

    if selected_range:
        sel_start, sel_end = selected_range
        ferie_per_giorno = ferie_per_giorno[
            (ferie_per_giorno["giorni_range"].dt.date >= sel_start) &
            (ferie_per_giorno["giorni_range"].dt.date <= sel_end)
        ]

    if ferie_per_giorno.empty:
        return None

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=ferie_per_giorno["giorni_range"],
            y=ferie_per_giorno["num_richieste"],
            mode="lines+markers",
            name="Richieste ferie",
            line=dict(color="#82cfff", width=3),
            marker=dict(size=8, color="#82cfff"),
        )
    )

    # Add holidays + weekends shading
    weekends = [
        d.date()
        for d in ferie_per_giorno["giorni_range"]
        if d.weekday() >= 5
    ]
    all_holidays = sorted(set(HOLIDAYS_FIXED) | set(weekends))

    for hday in all_holidays:
        x0 = datetime.datetime(hday.year, hday.month, hday.day) - datetime.timedelta(hours=12)
        x1 = x0 + datetime.timedelta(days=1)

        fig.add_vrect(
            x0=x0, x1=x1,
            fillcolor="rgba(0, 180, 0, 0.15)",
            layer="below",
            line_width=0,
        )

    fig.add_trace(
        go.Scatter(
            x=[None],
            y=[None],
            mode="markers",
            marker=dict(size=10, color="rgba(0, 180, 0, 0.4)"),
            name="Festività e weekend",
        )
    )

    fig.update_layout(
        title="Numero di richieste di ferie attive per giorno",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="white",
        xaxis=dict(title="Giorni", tickangle=-45, showgrid=False),
        yaxis=dict(title="Numero richieste ferie", dtick=1, rangemode="tozero"),
    )

    return fig
