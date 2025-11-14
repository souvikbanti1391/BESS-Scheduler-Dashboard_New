import plotly.express as px

def plot_last_7days(df):
    return px.line(df.tail(24*7), x='timestamp', y='mcp', title='Last 7 Days MCP')

def plot_forecast(df):
    return px.line(df, x='timestamp', y='mcp', title='Forecast')
