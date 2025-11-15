# frontend/utils/Report_Generator.py
# Lightweight PDF report generator using reportlab + Plotly (kaleido)
import io
import base64
from pathlib import Path
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

from plot_helpers import prepare_df, market_style_line, heatmap_last7_with_bands

# convert plotly fig to PNG bytes (kaleido required)
def fig_to_png_bytes(fig, width=1200, height=700):
    png_bytes = fig.to_image(format="png", width=width, height=height, scale=2)
    return io.BytesIO(png_bytes)

def load_dvc_logo_base64():
    candidates = [Path("frontend/assets/dvc_logo.png"), Path("frontend/assets/dvc_logo.jpg"), Path("frontend/assets/dvc_logo.png.jpg")]
    for p in candidates:
        if p.exists():
            b = p.read_bytes()
            return base64.b64encode(b).decode("ascii")
    return None

def build_summary_table(df):
    df = prepare_df(df)
    summary_data = [
        ["Summary Metric", "Value"],
        ["Start Date", str(df["timestamp"].min())],
        ["End Date", str(df["timestamp"].max())],
        ["Total Rows", len(df)],
        ["Avg MCP (Rs/kWh)", f"{df['mcp'].mean():.3f}"],
        ["Std Dev MCP", f"{df['mcp'].std():.3f}"],
        ["Min MCP", f"{df['mcp'].min():.3f}"],
        ["Max MCP", f"{df['mcp'].max():.3f}"]
    ]
    table = Table(summary_data, colWidths=[180, 260])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0f1117")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor("#1a1d26")),
        ('TEXTCOLOR', (0,1), (-1,-1), colors.white),
        ('BOX', (0,0), (-1,-1), 1, colors.gray),
        ('GRID', (0,0), (-1,-1), 0.3, colors.gray)
    ]))
    return table

def generate_pdf_report(df):
    df_clean = prepare_df(df)
    fig_market = market_style_line(df_clean)
    fig_heatmap = heatmap_last7_with_bands(df_clean)
    png_market = fig_to_png_bytes(fig_market)
    png_heat = fig_to_png_bytes(fig_heatmap)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    dvc_b64 = load_dvc_logo_base64()
    if dvc_b64:
        story.append(Image(io.BytesIO(base64.b64decode(dvc_b64)), width=70, height=70))
        story.append(Spacer(1, 12))

    story.append(Paragraph("<b>BESS Scheduler Intelligence — MCP Analysis Report</b>", styles["Title"]))
    story.append(Paragraph("Excel through Intelligence", styles["Heading3"]))
    story.append(Spacer(1, 15))

    story.append(Paragraph("<b>Dataset Summary</b>", styles["Heading2"]))
    story.append(Spacer(1, 6))
    story.append(build_summary_table(df_clean))
    story.append(Spacer(1, 24))

    story.append(Paragraph("<b>MCP Time Series — Market Style</b>", styles["Heading2"]))
    story.append(Spacer(1, 6))
    story.append(Image(png_market, width=460, height=270))
    story.append(Spacer(1, 24))

    story.append(Paragraph("<b>7-Day Charge/Discharge Opportunity Heatmap</b>", styles["Heading2"]))
    story.append(Spacer(1, 6))
    story.append(Image(png_heat, width=460, height=270))
    story.append(Spacer(1, 24))

    story.append(Spacer(1, 18))
    story.append(Paragraph("<i>Generated automatically by BESS Scheduler Intelligence</i>", styles["Italic"]))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
