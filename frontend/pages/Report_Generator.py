import streamlit as st
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table
from reportlab.lib.styles import getSampleStyleSheet
import tempfile, os
from utils.plot_helpers import plot_last_7days

st.title("PDF Report Generator")

df = st.session_state.get("uploaded_df")

if df is None:
    st.warning("⚠️ Upload MCP data from the sidebar first.")
    st.stop()

st.success("Using globally uploaded MCP data.")

if st.button("Generate PDF Report"):
    # create plot
    import plotly.io as pio
    fig = plot_last_7days(df)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
    pio.write_image(fig, tmp.name)

    # PDF
    path = "bess_report.pdf"
    doc = SimpleDocTemplate(path, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph("BESS Optimiser - MCP Report", styles["Title"]))
    story.append(Spacer(1, 12))
    story.append(RLImage(tmp.name, width=400, height=200))
    doc.build(story)

    with open(path, "rb") as f:
        st.download_button("Download Report", f, file_name="BESS_Report.pdf")
