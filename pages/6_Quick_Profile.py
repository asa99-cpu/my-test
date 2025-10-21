# pages/6_Quick_Profile.py
import io
from typing import Optional, Tuple

import numpy as np
import pandas as pd
import streamlit as st

# Altair for charts
import altair as alt

# Your existing loader (required)
try:
    from lib_data import sidebar_data_source  # must return (df: pd.DataFrame, source_label: str|None)
except Exception:
    sidebar_data_source = None

st.header("⚡ Quick Profile")

# ---------------- Load data ----------------
df: Optional[pd.DataFrame] = None
source_label: Optional[str] = None

if sidebar_data_source is not None:
    try:
        df, source_label = sidebar_data_source()
    except Exception as e:
        st.error(f"lib_data.sidebar_data_source() failed: {e}")

# Fallback to session_state if lib_data isn’t available
if df is None:
    df = st.session_state.get("filtered_df", st.session_state.get("df"))
    source_label = source_label or "(session_state)"

if df is None or df.empty:
    st.warning("No data available. Upload/select a dataset in the main app first.")
    st.stop()

st.caption(f"Source: **{source_label}** • Rows: **{len(df):,}** • Columns: **{df.shape[1]:,}**")

# ---------------- KPIs ----------------
missing_cells = int(df.isna().sum().sum())
duplicate_rows = int(df.duplicated().sum())

c1, c2, c3, c4 = st.columns(4)
c1.metric("Rows", f"{len(df):,}")
c2.metric("Columns", f"{df.shape[1]:,}")
c3.metric("Missing cells", f"{missing_cells:,}")
c4.metric("Duplicate rows", f"{duplicate_rows:,}")

st.divider()

# ---------------- Schema & Nulls (+ CSV) ----------------
st.subheader("Schema & Nulls")

schema = pd.DataFrame({
    "column": df.columns,
    "dtype": [str(df[c].dtype) for c in df.columns],
    "non_null": df.notna().sum().values,
    "nulls": df.isna().sum().values,
})
schema["pct_null"] = (schema["nulls"] / len(df) * 100).round(2)

st.dataframe(schema, use_container_width=True, hide_index=True)

schema_csv = schema.to_csv(index=False).encode("utf-8")
st.download_button(
    "Download Schema CSV",
    data=schema_csv,
    file_name="schema_nulls.csv",
    mime="text/csv",
)

st.divider()

# ---------------- Numeric Summary + Correlation Heatmap ----------------
num_cols = df.select_dtypes(include="number").columns.tolist()

st.subheader("Numeric Summary")
if num_cols:
    summary = df[num_cols].describe().T
    summary["missing"] = len(df) - summary["count"]
    st.dataframe(summary, use_container_width=True)

    st.markdown("**Correlation Heatmap**")
    corr = df[num_cols].corr(numeric_only=True)
    corr_long = (
        corr.reset_index()
            .melt(id_vars="index", var_name="variable", value_name="correlation")
            .rename(columns={"index": "feature"})
    )

    heat = (
        alt.Chart(corr_long)
        .mark_rect()
        .encode(
            x=alt.X("feature:N", sort=num_cols, title=""),
            y=alt.Y("variable:N", sort=num_cols, title=""),
            color=alt.Color("correlation:Q", scale=alt.Scale(scheme="blueorange"), title="r"),
            tooltip=["feature", "variable", alt.Tooltip("correlation:Q", format=".3f")],
        )
        .properties(height=400)
        .interactive()
    )
    st.altair_chart(heat, use_container_width=True)
else:
    st.info("No numeric columns detected.")

st.divider()

# ---------------- Distribution Explorer ----------------
st.subheader("Distribution Explorer")
if num_cols:
    sel_num = st.selectbox("Numeric column", num_cols, index=0)
    bins = st.slider("Bins", min_value=5, max_value=100, value=30, step=1)
    logy = st.checkbox("Log-scale Y", value=False)

    base = alt.Chart(df[[sel_num]]).transform_filter(
        alt.datum[sel_num] != None
    )
    hist = (
        base.mark_bar()
        .encode(
            x=alt.X(f"{sel_num}:Q", bin=alt.Bin(maxbins=bins), title=sel_num),
            y=alt.Y("count()", title="Count", scale=alt.Scale(type="log") if logy else alt.Undefined),
            tooltip=[alt.Tooltip(f"{sel_num}:Q", format=".3f"), alt.Tooltip("count():Q")],
        )
        .properties(height=300)
    )
    st.altair_chart(hist, use_container_width=True)
else:
    st.info("No numeric columns to explore.")

st.divider()

# ---------------- Categorical Overview (+ CSV) ----------------
st.subheader("Categorical Overview")
cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
if cat_cols:
    ccol = st.selectbox("Categorical column", cat_cols, index=0)
    topn = st.slider("Top N", min_value=5, max_value=50, value=15, step=1)

    vc = (
        df[ccol]
        .astype("string")
        .value_counts(dropna=False)
        .head(topn)
        .reset_index()
        .rename(columns={"index": ccol, ccol: "count"})
    )

    # Download CSV
    vc_csv = vc.to_csv(index=False).encode("utf-8")
    st.download_button(
        f"Download Top-{topn} '{ccol}' Frequencies",
        data=vc_csv,
        file_name=f"{ccol}_top{topn}_freq.csv",
        mime="text/csv",
    )

    # Bar chart
    bar = (
        alt.Chart(vc)
        .mark_bar()
        .encode(
            x=alt.X("count:Q", title="Count"),
            y=alt.Y(f"{ccol}:N", sort="-x", title=ccol),
            tooltip=[ccol, "count"],
        )
        .properties(height=max(120, 24 * len(vc)))
    )
    st.altair_chart(bar, use_container_width=True)
else:
    st.info("No categorical columns detected.")

st.divider()

# ---------------- Sample Rows ----------------
st.subheader("Sample Rows")
n_show = st.slider("Rows to show", min_value=5, max_value=min(200, len(df)), value=min(20, len(df)))
st.dataframe(df.head(n_show), use_container_width=True)

st.caption("✅ This is a standalone page. No other files need changes.")
