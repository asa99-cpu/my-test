import streamlit as st
import pandas as pd
from pathlib import Path
from utils import read_csv_safely, demo_weather, find_datetime_columns, numeric_columns

st.set_page_config(page_title="CSV Explorer", page_icon="📈", layout="centered")
st.title("📈 CSV Explorer")
st.caption("Load a CSV, filter by date, explore stats, and plot one or more metrics.")

# ---------------- Sidebar: Data ----------------
with st.sidebar:
    st.header("Data")
    uploaded = st.file_uploader("Upload CSV", type=["csv"])
    fallback_path = Path("data") / "weather.csv"

    if uploaded is not None:
        df = read_csv_safely(uploaded)
        source_label = "Uploaded file"
    elif fallback_path.exists():
        df = read_csv_safely(fallback_path)
        source_label = f"{fallback_path}"
    else:
        st.info("No file uploaded and no local CSV found — using demo data.")
        df = demo_weather()
        source_label = "Demo dataset"

    if df is None or df.empty:
        st.error("No data to show.")
        st.stop()

    st.caption(f"Source: **{source_label}** • Rows: **{len(df):,}** • Columns: **{len(df.columns)}**")

    # Detect date and numeric columns
    dt_cols = find_datetime_columns(df)
    num_cols = numeric_columns(df)

    # Store in session for access by other pages
    st.session_state.df = df
    st.session_state.dt_cols = dt_cols
    st.session_state.num_cols = num_cols
