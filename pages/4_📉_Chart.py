import streamlit as st
import pandas as pd
from utils import resample_df, apply_rolling, normalize_01

st.header("📉 Chart")

# --- guards ---
if "df" not in st.session_state:
    st.warning("Please upload a CSV in the main page first.")
    st.stop()

# Work on the filtered view if it exists, else the full df
df = st.session_state.get("filtered_df", st.session_state.df)

# Re-detect columns on THIS df (safer than relying on earlier session values)
num_cols = df.select_dtypes(include="number").columns.tolist()
dt_cols = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]

if not num_cols:
    st.info("No numeric columns found to plot.")
    st.stop()

# --- UI ---
metrics = st.multiselect(
    "Metrics to plot",
    options=num_cols,
    default=[num_cols[0]] if num_cols else [],
    help="Choose one or more numeric columns."
)

chart_kind = st.selectbox("Chart type", ["Line", "Area", "Bar"])
freq = st.selectbox("Resample frequency (if a date column is selected)", ["Off", "D", "W", "M"])
agg = st.radio("Aggregation", ["Mean", "Sum"], horizontal=True)
roll = st.slider("Rolling average window", 1, 60, 1, help="Applied after resampling.")
norm = st.checkbox("Normalize 0–1 (min–max)")

# Optional date column
date_col = st.selectbox(
    "Date column (optional, enables resampling)",
    options=["(none)"] + dt_cols,
    index=0
)

# --- sanitize selections vs current DataFrame columns ---
available = set(df.columns)
missing = [c for c in metrics if c not in available]
metrics = [c for c in metrics if c in available]

if missing:
    st.warning(f"Dropped missing columns: {', '.join(missing)} (not in current data).")

if not metrics:
    st.info("Pick at least one existing numeric column to plot.")
    st.stop()

# --- build the plotting frame ---
if date_col != "(none)":
    # Ensure datetime dtype
    if not pd.api.types.is_datetime64_any_dtype(df[date_col]):
        # try to coerce if user picked a non-datetime column that looks like dates
        try:
            df = df.copy()
            df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        except Exception:
            pass

    f = None if freq == "Off" else freq
    df_chart = resample_df(df, date_col, metrics, f, agg)
else:
    # No date column; just take the selected metrics
    df_chart = df[metrics]

# Rolling + normalization
if roll > 1:
    df_chart = apply_rolling(df_chart, roll)
if norm:
    # Normalize only numeric columns to avoid errors after resample
    num_only = df_chart.select_dtypes(include="number").columns
    df_chart[num_only] = normalize_01(df_chart[num_only])

# --- plot ---
if df_chart.empty:
    st.warning("Nothing to plot with the current filters/selections.")
else:
    if chart_kind == "Line":
        st.line_chart(df_chart, use_container_width=True)
    elif chart_kind == "Area":
        st.area_chart(df_chart, use_container_width=True)
    else:
        st.bar_chart(df_chart, use_container_width=True)
