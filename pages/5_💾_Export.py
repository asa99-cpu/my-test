import streamlit as st

st.header("💾 Export Data")

if "filtered_df" in st.session_state:
    df = st.session_state.filtered_df
else:
    df = st.session_state.get("df")

if df is None:
    st.warning("No data loaded.")
else:
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button("Download as CSV", csv_bytes, "filtered.csv", "text/csv")
