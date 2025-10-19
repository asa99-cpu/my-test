import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(page_title="CSV Viewer", page_icon="📈", layout="centered")

DATA_PATH = Path("data") / "weather.csv"

st.title("CSV Viewer (Streamlit)")
st.caption("Reads data/weather.csv and shows a table, summary, and a line chart.")

@st.cache_data(show_spinner=False)
def load_csv(p: Path) -> pd.DataFrame | None:
    if not p.exists():
        return None
    df = pd.read_csv(p)
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    return df

df = load_csv(DATA_PATH)

if df is None:
    st.error(f"CSV not found at {DATA_PATH}. Make sure the file exists.")
    st.stop()

# Raw data
st.subheader("Raw Data")
st.dataframe(df, width="stretch")  # ✅ new API (replaces use_container_width)

# Summary (make it pandas-version-safe)
st.subheader("Summary Statistics")
numeric_cols = df.select_dtypes(include="number").columns.tolist()
if numeric_cols:
    summary = df[numeric_cols].describe()
    st.dataframe(summary, width="stretch")
else:
    st.info("No numeric columns found to summarize.")

# Optional date filter
has_dt = "Date" in df.columns and pd.api.types.is_datetime64_any_dtype(df["Date"])
if has_dt:
    dmin, dmax = df["Date"].min(), df["Date"].max()
    if pd.notna(dmin) and pd.notna(dmax):
        st.subheader("Filter")
        start, end = st.date_input(
            "Date range:",
            value=(dmin.date(), dmax.date()),
            min_value=dmin.date(),
            max_value=dmax.date(),
        )
        if start and end:
            mask = (df["Date"] >= pd.to_datetime(start)) & (df["Date"] <= pd.to_datetime(end))
            df = df.loc[mask].copy()

# Chart
st.subheader("Chart")
numeric_cols = df.select_dtypes(include="number").columns.tolist()
if not numeric_cols:
    st.warning("No numeric columns to plot.")
else:
    metric = st.selectbox("Select a numeric column to plot:", numeric_cols, index=0)
    if has_dt:
        chart_data = df.set_index("Date")[[metric]].sort_index()
    else:
        chart_data = df[[metric]]

    # ❗ Do NOT pass width="stretch" here — Altair expects a number.
    # Also avoid use_container_width (deprecated). Let Streamlit auto-size.
    st.line_chart(chart_data)