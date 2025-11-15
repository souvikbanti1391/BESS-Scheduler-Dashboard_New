# frontend/utils/plot_helpers.py
# ============================================================
# Plot helpers for IEX Predictor — Dark theme, market-style chart
# - prepare_df: cleans & scales MCP to Rs/kWh
# - market_style_line: full-width stock-like line with weekend bands,
#                     separators, day labels, animated transitions
# - heatmap_last7_with_bands: 7-day hourly heatmap with bands
# ============================================================

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import timedelta

# ---------------------------
# Data preparation
# ---------------------------
def prepare_df(df):
    """
    Clean + sort + convert MCP to Rs/kWh if uploaded as Rs/MWh.
    Ensures columns:
      - timestamp (datetime)
      - mcp (float, Rs/kWh)
      - hour (0..23)
      - date_str (YYYY-MM-DD)
      - delta (mcp - prev)
    """
    df = df.copy()

    # If there's no 'timestamp', attempt common fallbacks
    if "timestamp" not in df.columns:
        for col in ["date_time", "DateTime", "Date", "date", "datetime"]:
            if col in df.columns:
                df["timestamp"] = df[col]
                break
        # If still not found, try Date + Hour columns
        if "timestamp" not in df.columns and {"Date", "Hour"}.issubset(set(df.columns)):
            try:
                df["timestamp"] = pd.to_datetime(df["Date"].astype(str) + " " + df["Hour"].astype(str), errors="coerce")
            except Exception:
                pass

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)

    # Identify MCP column
    mcp_candidates = [c for c in df.columns if c.lower() in ("mcp", "price", "mcp_inr", "mcp_inr/kwh", "mcp_rs")]
    if not mcp_candidates:
        numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) and c != "timestamp"]
        mcp_col = numeric_cols[0] if numeric_cols else None
    else:
        mcp_col = mcp_candidates[0]

    if mcp_col is None:
        raise ValueError("No numeric MCP/price column found in the uploaded file. Ensure a price column exists.")

    df["mcp"] = pd.to_numeric(df[mcp_col], errors="coerce")
    df = df.dropna(subset=["mcp"]).reset_index(drop=True)

    # Auto-detect units: if typical values are >>100 (e.g., 2000), assume Rs/MWh and convert
    if df["mcp"].max() > 100:
        df["mcp"] = df["mcp"] / 1000.0

    df["hour"] = df["timestamp"].dt.hour
    df["date_str"] = df["timestamp"].dt.strftime("%Y-%m-%d")
    df["dow"] = df["timestamp"].dt.day_name()
    df["delta"] = df["mcp"].diff().fillna(0.0)

    return df


# ---------------------------
# Helper: create weekend bands & separators & day labels
# ---------------------------
def _create_day_shapes_and_annotations(df, y_min=None, y_max=None, saturday_color="rgba(70,70,120,0.12)", sunday_color="rgba(80,40,120,0.16)"):
    """
    Returns tuple (shapes, annotations)
    shapes: rectangle bands for Saturday/Sunday and vertical dotted separators
    annotations: day labels at top of each day's band
    """
    shapes = []
    annotations = []

    if df.empty:
        return shapes, annotations

    # Determine full-day boundaries using UTC midnight of each day in the timestamps timezone
    df = df.copy()
    df["date_only"] = df["timestamp"].dt.normalize()  # midnight
    unique_dates = df["date_only"].drop_duplicates().sort_values().tolist()

    # If y_min/y_max not provided, compute defaults
    if y_min is None or y_max is None:
        y_min = float(df["mcp"].min() * 0.98)
        y_max = float(df["mcp"].max() * 1.02)

    for d in unique_dates:
        day_name = d.day_name()
        start = d
        end = d + timedelta(days=1)
        # Saturday
        if day_name.lower().startswith("saturday"):
            shapes.append(dict(
                type="rect",
                xref="x",
                yref="paper",
                x0=start,
                x1=end,
                y0=0,
                y1=1,
                fillcolor=saturday_color,
                opacity=1,
                layer="below",
                line_width=0
            ))
        # Sunday
        if day_name.lower().startswith("sunday"):
            shapes.append(dict(
                type="rect",
                xref="x",
                yref="paper",
                x0=start,
                x1=end,
                y0=0,
                y1=1,
                fillcolor=sunday_color,
                opacity=1,
                layer="below",
                line_width=0
            ))

        # Vertical dotted separator at midnight (except first)
        shapes.append(dict(
            type="line",
            xref="x",
            yref="y",
            x0=start,
            x1=start,
            y0=y_min,
            y1=y_max,
            line=dict(color="rgba(200,200,200,0.12)", width=1, dash="dot"),
            layer="above"
        ))

        # Day label annotation at the top
        annotations.append(dict(
            x=start + timedelta(hours=12),
            y=y_max,
            xref="x",
            yref="y",
            text=d.strftime("%a").upper(),
            showarrow=False,
            font=dict(color="rgba(200,200,200,0.35)", size=11),
            xanchor="center",
            yanchor="bottom",
            bgcolor="rgba(0,0,0,0)"
        ))

    return shapes, annotations


# ---------------------------
# Market-style line (dark theme)
# ---------------------------
def market_style_line(df,
                      title="MCP (Rs/kWh) — Market Style",
                      line_color="#39D98A",   # mint green
                      area_fill="rgba(57,217,138,0.12)",
                      smoothing=True):
    """
    Returns a Plotly Figure tailored for a dark-themed market style visualization.
    - weekend shading (Sat & Sun)
    - dotted day separators
    - day labels
    - animated transitions enabled via layout.transition
    - crosshair + rich hover template
    """
    df = prepare_df(df)

    if df.empty:
        raise ValueError("No data after parsing.")

    # Optionally compute a smooth line via rolling mean (small window)
    plot_x = df["timestamp"]
    plot_y = df["mcp"]

    if smoothing and len(df) >= 5:
        # a mild rolling window (3) to smooth jitter without losing spikes
        y_smooth = df["mcp"].rolling(window=3, min_periods=1, center=True).mean()
    else:
        y_smooth = plot_y

    vmin = float(np.nanmin(plot_y))
    vmax = float(np.nanmax(plot_y))

    fig = go.Figure()

    # area (fill) - subtle
    fig.add_trace(go.Scatter(
        x=plot_x,
        y=y_smooth,
        mode="lines",
        line=dict(color=line_color, width=2.5),
        fill="tozeroy",
        fillcolor=area_fill,
        hoverinfo="skip",
        name="MCP area"
    ))

    # thin invisible marker trace for hover + crosshair details (we show custom hover)
    fig.add_trace(go.Scatter(
        x=plot_x,
        y=plot_y,
        mode="markers",
        marker=dict(size=6, color="rgba(0,0,0,0)"),
        showlegend=False,
        hovertemplate=(
            "<b>%{y:.3f} Rs/kWh</b><br>"
            "%{x|%a, %d %b %Y}<br>"
            "%{x|%H:%M} — %{customdata[0]}<br>"
            "Δ prev hr: %{customdata[1]:+.3f} Rs/kWh<extra></extra>"
        ),
        customdata=np.vstack([df["dow"].values, df["delta"].values]).T
    ))

    # Layout: dark, crosshair
    shapes, annotations = _create_day_shapes_and_annotations(df, y_min=vmin * 0.98, y_max=vmax * 1.02)

    fig.update_layout(
        title=title,
        xaxis=dict(
            type="date",
            showspikes=True,
            spikemode="across",
            spikecolor="rgba(255,255,255,0.08)",
            spikesnap="cursor",
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1D", step="day", stepmode="backward"),
                    dict(count=7, label="7D", step="day", stepmode="backward"),
                    dict(count=30, label="1M", step="day", stepmode="backward"),
                    dict(step="all", label="All")
                ])
            ),
            rangeslider=dict(visible=True),
            tickformat="%d-%b %H:%M"
        ),
        yaxis=dict(title="MCP (Rs/kWh)"),
        template="plotly_dark",
        plot_bgcolor="rgba(8,10,15,1)",
        paper_bgcolor="rgba(8,10,15,1)",
        height=520,
        hovermode="x unified",
        shapes=shapes,
        annotations=annotations,
        transition=dict(duration=450, easing="cubic-in-out")
    )

    # Add a subtle top margin for day labels not to overlap
    fig.update_layout(margin=dict(t=80, b=60, l=60, r=40))

    return fig


# ---------------------------
# Heatmap last 7 days with banding for arbitrage
# ---------------------------
def heatmap_last7_with_bands(df, low_pct=20, high_pct=80, title="Last 7 days — Hourly MCP (banded)"):
    """
    Builds a heatmap for the last 7 days (168 hours) with color-banding:
      - bottom low_pct percentile => 'best charge' (blue/green)
      - top high_pct percentile => 'best discharge' (red/orange)
      - middle => neutral (light colors)
    Returns Plotly Figure.
    """
    df = prepare_df(df)

    # Focus on last 7 days of data based on timestamp
    max_ts = df["timestamp"].max()
    start_ts = max_ts - pd.Timedelta(days=7)
    df7 = df[df["timestamp"] >= start_ts].copy()

    if df7.empty:
        df7 = df.tail(24 * 7).copy()

    if df7.empty:
        raise ValueError("Not enough data to build 7-day heatmap.")

    pivot = df7.pivot_table(values="mcp", index="date_str", columns="hour", aggfunc="mean")
    pivot = pivot.reindex(columns=list(range(24)), fill_value=np.nan)

    all_vals = pivot.values.flatten()
    all_vals = all_vals[~np.isnan(all_vals)]
    if len(all_vals) == 0:
        raise ValueError("No numeric MCP values found for heatmap.")

    low_thresh = np.nanpercentile(all_vals, low_pct)
    high_thresh = np.nanpercentile(all_vals, high_pct)

    z = pivot.values.copy()
    band = np.full_like(z, np.nan, dtype=float)
    band[np.where(z <= low_thresh)] = 0.0
    band[np.where((z > low_thresh) & (z < high_thresh))] = 1.0
    band[np.where(z >= high_thresh)] = 2.0

    x = [f"{h:02d}:00" for h in pivot.columns]
    y = pivot.index.tolist()

    colorscale = [
        [0.0, "rgb(28,120,220)"],   # blue - best charge
        [0.333, "rgb(28,120,220)"],
        [0.333, "rgb(120,120,120)"], # neutral grey
        [0.666, "rgb(120,120,120)"],
        [0.666, "rgb(245,80,60)"],   # red - best discharge
        [1.0, "rgb(245,80,60)"]
    ]

    fig = go.Figure(data=go.Heatmap(
        z=band,
        x=x,
        y=y,
        hovertemplate="Date: %{y}<br>Hour: %{x}<br>MCP: %{customdata:.3f} Rs/kWh<extra></extra>",
        customdata=np.round(z, 3),
        colorscale=colorscale,
        colorbar=dict(
            tickmode="array",
            tickvals=[0, 1, 2],
            ticktext=[f"Charge ≤{low_pct}%", "Neutral", f"Discharge ≥{high_pct}%"],
            title="Band"
        )
    ))

    fig.update_layout(
        title=title + f" (bands: charge ≤{low_pct}%, discharge ≥{high_pct}%)",
        xaxis_title="Hour of day",
        yaxis_title="Date",
        template="plotly_dark",
        height=560,
        margin=dict(t=72, b=40, l=60, r=40)
    )

    return fig
