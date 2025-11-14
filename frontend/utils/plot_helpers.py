import plotly.graph_objects as go
import pandas as pd

def prepare_df(df):
    """
    Clean + sort + convert MCP to Rs/kWh if uploaded as Rs/MWh.
    """
    df = df.copy()

    # Ensure timestamps parsed
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    df = df.dropna(subset=['timestamp'])

    # Sort by timestamp
    df = df.sort_values('timestamp')

    # Convert Rs/MWh → Rs/kWh if too large
    # Typical MCP: 2–20 Rs/kWh  => Rs/MWh will be ~2000–20000
    if df['mcp'].max() > 100:     # auto-detect scaling
        df['mcp'] = df['mcp'] / 1000.0

    return df


def plot_last_7days(df):
    """
    Plot last 7 days MCP with clean datetime axis + colored line.
    """
    df = prepare_df(df)

    # Extract last 7 days (168 hours)
    last = df.tail(24*7)

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=last['timestamp'],
        y=last['mcp'],
        mode='lines+markers',
        line=dict(color='green', width=3),
        marker=dict(size=5, color='orange'),
        name="Last 7 Days MCP"
    ))

    fig.update_layout(
        title="Last 7 Days MCP Trend (Rs/kWh)",
        xaxis_title="Timestamp",
        yaxis_title="MCP (Rs/kWh)",
        template="plotly_white",
        xaxis=dict(showgrid=True, tickformat="%d-%b %H:%M"),
        yaxis=dict(showgrid=True),
        height=450
    )

    return fig


def plot_forecast(df):
    """
    Clean forecast plot with consistent style.
    """
    df = prepare_df(df)

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['mcp'],
        mode='lines+markers',
        line=dict(color='blue', width=3),
        marker=dict(size=4, color='red'),
        name="Forecast MCP"
    ))

    fig.update_layout(
        title="Forecasted MCP (Rs/kWh)",
        xaxis_title="Timestamp",
        yaxis_title="MCP (Rs/kWh)",
        template="plotly_white",
        xaxis=dict(showgrid=True, tickformat="%d-%b %H:%M"),
        yaxis=dict(showgrid=True),
        height=450
    )

    return fig
