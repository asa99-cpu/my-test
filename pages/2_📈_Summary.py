import streamlit as st
import pandas as pd

st.header("📈 Summary Statistics")

if "df" not in st.session_state:
    st.warning("Please upload a CSV in the main page first.")
else:
    df = st.session_state.df
    num_cols = st.session_state.num_cols
    if num_cols:
        st.dataframe(df[num_cols].describe(), use_container_width=True)
    else:
        st.info("No numeric columns to summarize.")
