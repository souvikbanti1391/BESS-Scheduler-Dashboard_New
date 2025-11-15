# ============================================================
#   plot_helpers.py — Full Final Version
#   DO NOT EDIT — Required for Predictor Page
# ============================================================

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px


# ------------------------------------------------------------
#   Base DF cleaner
# ------------------------------------------------------------
def prepare_df(df):
    """
    Clean + sort + convert MCP to Rs/kWh if uploaded as Rs/MWh.
    Adds: hour, date, delta.
    """
    df = df.copy()

    # timestamp parsing
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"]).sort_values("timestamp")

    # mcp parsing + scaling
    df["mcp"] = pd.to_numeric(df["mcp"], errors="coerce")
    df = df.dropna(subset=["mcp"])

    # Rs/MWh → Rs/kWh scaling
    if df["mcp"].max() > 100:
        df["mcp"] = df["mcp"] / 1000.0

    df["hour"] = df["timestamp"].dt.hour
    df["date"] = df["timestamp"].dt.date
    df["date_str"] = df["timestamp"].dt.strftime("%Y-%m-%d")
    df["delta"] = df["mcp"].diff().fillna(0.0)

    return df


# ------------------------------------------------------------
#   Trend plot: Gradient Line + Delta Tooltip
# ------------------------------------------------------------
def gradient_line_with_delta(df, color_low="green", color_high="red"):
    """
    Line plot over time with markers colored by MCP (gradient),
    hover shows delta from previous hour.
    """
    df = prepare_df(df)

    vals = df["mcp"].values
    vmin = float(np.nanmin(vals))
    vmax = float(np.nanmax(vals))
    if vmax - vmin < 1e-6:
        vmax = vmin + 1.0

    fig = go.Figure()

    # Base line
    fig.add_trace(go.Scatter(
        x=df["timestamp"],
        y=df["mcp"],
        mode="lines",
        line=dict(color="rgba(50,50,200,0.8)", width=2),
        name="MCP Line"
    ))

    # Colored markers
    fig.add_trace(go.Scatter(
        x=df["timestamp"],
        y=df["mcp"],
        mode="markers",
        marker=dict(
            size=6,
            color=df["mcp"],
            colorscale=[[0, color_low], [1, color_high]],
            cmin=vmin,
            cmax=vmax,
            colorbar=dict(title="Rs/kWh")
        ),
        customdata=df["delta"].values.reshape(-1, 1),
        hovertemplate=(
            "Timestamp: %{x}<br>"
            "MCP: %{y:.3f} Rs/kWh<br>"
            "Δ Prev Hr: %{customdata[0]:.3f} Rs/kWh"
        ),
        name="MCP Points"
    ))

    fig.update_layout(
        title="MCP Trend (Last 7 Days + Hourly Delta)",
        xaxis_title="Timestamp",
        yaxis_title="MCP (Rs/kWh)",
        template="plotly_white",
        xaxis=dict(showgrid=True, tickformat="%d-%b %H:%M"),
        height=480
    )

    return fig


# ------------------------------------------------------------
#   Heatmap: Hour of Day × Date
# ------------------------------------------------------------
def heatmap_hour_by_date(df):
    df = prepare_df(df)

    pivot = df.pivot_table(values="mcp", index="date_str", columns="hour", aggfunc="mean")
    pivot = pivot.reindex(columns=list(range(24)), fill_value=np.nan)

    z = pivot.values
    x = [f"{h:02d}:00" for h in pivot.columns]
    y = pivot.index

    fig = go.Figure(data=go.Heatmap(
        z=z,
        x=x,
        y=y,
        colorscale="YlOrRd",
        colorbar=dict(title="Rs/kWh"),
    ))

    fig.update_layout(
        title="Hourly MCP Heatmap (Date × Hour)",
        xaxis_title="Hour of Day",
        yaxis_title="Date",
        template="plotly_white",
        height=600
    )

    return fig


# ------------------------------------------------------------
#   Daily Profile Comparison
# ------------------------------------------------------------
def daily_profile_comparison(df, normalize=False):
    df = prepare_df(df)

    grouped = df.groupby(["date_str", "hour"])["mcp"].mean().reset_index()
    pivot = grouped.pivot(index="hour", columns="date_str", values="mcp")

    fig = go.Figure()

    for day in pivot.columns:
        y = pivot[day].values

        if normalize:
            if np.nanmax(y) - np.nanmin(y) > 1e-6:
                y = (y - np.nanmin(y)) / (np.nanmax(y) - np.nanmin(y))

        fig.add_trace(go.Scatter(
            x=pivot.index,
            y=y,
            mode="lines+markers",
            name=str(day),
            hovertemplate="Hour: %{x}<br>MCP: %{y:.3f}"
        ))

    fig.update_layout(
        title="Daily Profile Comparison",
        xaxis_title="Hour of Day",
        yaxis_title="MCP (Rs/kWh)" + (" (Normalized)" if normalize else ""),
        template="plotly_white",
        height=520
    )

    return fig


# ------------------------------------------------------------
#   MCP Histogram
# ------------------------------------------------------------
def mcp_histogram(df):
    df = prepare_df(df)

    fig = px.histogram(
        df,
        x="mcp",
        nbins=50,
        title="MCP Distribution Histogram",
        labels={"mcp": "MCP (Rs/kWh)"}
    )

    fig.update_layout(template="plotly_white", height=420)
    return fig
