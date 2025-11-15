# frontend/utils/plot_helpers.py
# Lightweight plot helpers for frontend (NO SciPy, NO heavy ML libs)

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import timedelta
import math

# ---------------------------
# Data preparation
# ---------------------------
def prepare_df(df):
    df = df.copy()
    # try common timestamp columns
    if "timestamp" not in df.columns:
        for col in ["date_time", "DateTime", "Date", "date", "datetime", "TIME"]:
            if col in df.columns:
                df["timestamp"] = df[col]
                break
        # Date + Hour fallback
        if "timestamp" not in df.columns and {"Date", "Hour"}.issubset(set(df.columns)):
            try:
                df["timestamp"] = pd.to_datetime(df["Date"].astype(str) + " " + df["Hour"].astype(str), errors="coerce")
            except Exception:
                pass

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)

    # find numeric price column
    candidates = [c for c in df.columns if c.lower() in ("mcp", "price", "mcp_inr", "mcp_rs", "price_inr")]
    if candidates:
        mcp_col = candidates[0]
    else:
        numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) and c != "timestamp"]
        mcp_col = numeric_cols[0] if numeric_cols else None

    if mcp_col is None:
        raise ValueError("No numeric MCP/price column found. Ensure file has a price column.")

    df["mcp"] = pd.to_numeric(df[mcp_col], errors="coerce")
    df = df.dropna(subset=["mcp"]).reset_index(drop=True)

    # Auto-scale Rs/MWh -> Rs/kWh if values large
    if df["mcp"].max() > 100:
        df["mcp"] = df["mcp"] / 1000.0

    df["hour"] = df["timestamp"].dt.hour
    df["date_str"] = df["timestamp"].dt.strftime("%Y-%m-%d")
    df["dow"] = df["timestamp"].dt.day_name()
    df["delta"] = df["mcp"].diff().fillna(0.0)

    return df


# ---------------------------
# Day shapes (weekend bands & separators)
# ---------------------------
def _create_day_shapes_and_annotations(df, y_min=None, y_max=None,
                                       saturday_color="rgba(70,70,120,0.08)",
                                       sunday_color="rgba(80,40,120,0.12)"):
    shapes = []
    annotations = []
    if df.empty:
        return shapes, annotations

    df = df.copy()
    df["date_only"] = df["timestamp"].dt.normalize()
    unique_dates = df["date_only"].drop_duplicates().sort_values().tolist()

    if y_min is None or y_max is None:
        if not df["mcp"].empty:
            y_min = float(df["mcp"].min() * 0.98)
            y_max = float(df["mcp"].max() * 1.02)
        else:
            y_min, y_max = 0, 1

    for d in unique_dates:
        day_name = d.strftime("%A")
        start = d
        end = d + timedelta(days=1)
        if day_name.lower().startswith("saturday"):
            shapes.append(dict(type="rect", xref="x", yref="paper", x0=start, x1=end, y0=0, y1=1, fillcolor=saturday_color, opacity=1, layer="below", line_width=0))
        if day_name.lower().startswith("sunday"):
            shapes.append(dict(type="rect", xref="x", yref="paper", x0=start, x1=end, y0=0, y1=1, fillcolor=sunday_color, opacity=1, layer="below", line_width=0))

        shapes.append(dict(type="line", xref="x", yref="y", x0=start, x1=start, y0=y_min, y1=y_max, line=dict(color="rgba(200,200,200,0.08)", width=1, dash="dot"), layer="above"))

        annotations.append(dict(x=start + timedelta(hours=12), y=y_max, xref="x", yref="y", text=d.strftime("%a").upper(), showarrow=False, font=dict(color="rgba(200,200,200,0.28)", size=11), xanchor="center", yanchor="bottom"))

    return shapes, annotations


# ---------------------------
# Market-style line (dark)
# ---------------------------
def market_style_line(df, title="MCP (Rs/kWh) — Market Style", line_color="#39D98A", area_fill="rgba(57,217,138,0.10)", smoothing=True):
    df = prepare_df(df)
    if df.empty:
        raise ValueError("No data after parsing.")

    plot_x = df["timestamp"]
    plot_y = df["mcp"]

    if smoothing and len(df) >= 5:
        y_smooth = df["mcp"].rolling(window=3, min_periods=1, center=True).mean()
    else:
        y_smooth = plot_y

    vmin = float(np.nanmin(plot_y))
    vmax = float(np.nanmax(plot_y))
    if math.isclose(vmin, vmax):
        vmax = vmin + 1.0

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=plot_x, y=y_smooth, mode="lines", line=dict(color=line_color, width=2.6), fill="tozeroy", fillcolor=area_fill, hoverinfo="skip", name="MCP"))
    customdata = np.vstack([df["dow"].values, df["delta"].values]).T
    fig.add_trace(go.Scatter(x=plot_x, y=plot_y, mode="markers", marker=dict(size=6, color="rgba(0,0,0,0)"), showlegend=False,
                             hovertemplate=("<b>%{y:.3f} Rs/kWh</b><br>%{x|%a, %d %b %Y}<br>%{x|%H:%M} — %{customdata[0]}<br>Δ prev hr: %{customdata[1]:+.3f} Rs/kWh<extra></extra>"),
                             customdata=customdata))

    shapes, annotations = _create_day_shapes_and_annotations(df, y_min=vmin * 0.98, y_max=vmax * 1.02)
    fig.update_layout(title=title,
                      xaxis=dict(type="date", showspikes=True, spikemode="across", spikecolor="rgba(255,255,255,0.06)", spikesnap="cursor",
                                 rangeselector=dict(buttons=list([
                                     dict(count=1, label="1D", step="day", stepmode="backward"),
                                     dict(count=7, label="7D", step="day", stepmode="backward"),
                                     dict(count=30, label="1M", step="day", stepmode="backward"),
                                     dict(step="all", label="All")
                                 ])),
                                 rangeslider=dict(visible=True),
                                 tickformat="%d-%b %H:%M"),
                      yaxis=dict(title="MCP (Rs/kWh)"),
                      template="plotly_dark",
                      plot_bgcolor="rgba(8,10,15,1)",
                      paper_bgcolor="rgba(8,10,15,1)",
                      height=520,
                      hovermode="x unified",
                      shapes=shapes,
                      annotations=annotations,
                      transition=dict(duration=400, easing="cubic-in-out"))
    fig.update_layout(margin=dict(t=80, b=60, l=60, r=40))
    return fig


# ---------------------------
# Heatmap last 7 days with banding
# ---------------------------
def heatmap_last7_with_bands(df, low_pct=20, high_pct=80, title="Last 7 days — Hourly MCP (banded)"):
    df = prepare_df(df)
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
        raise ValueError("No numeric MCP values for heatmap.")

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
        [0.0, "rgb(28,120,220)"],
        [0.333, "rgb(28,120,220)"],
        [0.333, "rgb(120,120,120)"],
        [0.666, "rgb(120,120,120)"],
        [0.666, "rgb(245,80,60)"],
        [1.0, "rgb(245,80,60)"]
    ]

    fig = go.Figure(data=go.Heatmap(z=band, x=x, y=y,
                                   hovertemplate="Date: %{y}<br>Hour: %{x}<br>MCP band: %{z}<extra></extra>",
                                   colorscale=colorscale,
                                   colorbar=dict(tickmode="array", tickvals=[0,1,2], ticktext=[f"Charge ≤{low_pct}%", "Neutral", f"Discharge ≥{high_pct}%"], title="Band")
                                   ))
    fig.update_layout(title=title + f" (bands: charge ≤{low_pct}%, discharge ≥{high_pct}%)",
                      xaxis_title="Hour of day", yaxis_title="Date", template="plotly_dark", height=560, margin=dict(t=72,b=40,l=60,r=40))
    return fig


# ---------------------------
# Forecast plot with CI (z-value fixed)
# ---------------------------
def plot_forecast_with_ci(history_df, forecast_df, ci=0.9):
    # simple CI using historical volatility (no SciPy)
    history = prepare_df(history_df)
    forecast = forecast_df.copy()
    forecast["timestamp"] = pd.to_datetime(forecast["timestamp"], errors="coerce")
    forecast["mcp"] = pd.to_numeric(forecast["mcp"], errors="coerce")

    recent = history.tail(24 * 7)
    if recent.empty:
        sigma = float(history["mcp"].std()) if not history["mcp"].empty else 0.0
    else:
        sigma = float(recent["mcp"].diff().std())
        if np.isnan(sigma) or sigma <= 0:
            sigma = float(history["mcp"].std() if not history["mcp"].empty else 0.0)

    # Use precomputed z for CI (no SciPy)
    # 90% CI => z ~= 1.645; 95% CI => 1.96
    if ci >= 0.95:
        z = 1.96
    elif ci >= 0.90:
        z = 1.645
    else:
        z = 1.28

    forecast["lower"] = forecast["mcp"] - z * sigma
    forecast["upper"] = forecast["mcp"] + z * sigma

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=history["timestamp"], y=history["mcp"], mode="lines", name="History", line=dict(color="rgba(180,180,200,0.9)", width=1.8)))
    fig.add_trace(go.Scatter(x=forecast["timestamp"], y=forecast["mcp"], mode="lines+markers", name="Forecast", line=dict(color="#39D98A", width=2.4)))
    fig.add_trace(go.Scatter(x=list(forecast["timestamp"]) + list(forecast["timestamp"][::-1]),
                             y=list(forecast["upper"]) + list(forecast["lower"][::-1]),
                             fill="toself", fillcolor="rgba(57,217,138,0.12)", line=dict(color="rgba(255,255,255,0)"), hoverinfo="skip",
                             showlegend=True, name=f"{int(ci*100)}% CI"))
    fig.update_layout(title=f"Forecast + {int(ci*100)}% Confidence Interval", xaxis=dict(type="date", tickformat="%d-%b %H:%M"),
                      yaxis=dict(title="MCP (Rs/kWh)"), template="plotly_dark", height=520, hovermode="x unified", transition=dict(duration=350, easing="cubic-in-out"))
    return fig
