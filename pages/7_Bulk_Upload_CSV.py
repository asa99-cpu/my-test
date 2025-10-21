# pages/7_Bulk_Upload_CSV.py
import os
import io
import re
from typing import List, Optional, Tuple

import pandas as pd
import numpy as np
import streamlit as st


st.header("📥 Bulk Upload CSV")

# ---------------- Helpers ----------------
def standardize_columns(cols: List[str]) -> List[str]:
    """lowercase, trim, collapse spaces/punct to single underscore, ensure uniqueness."""
    def _clean(c: str) -> str:
        c = (c or "").strip().lower()
        c = re.sub(r"\s+", "_", c)
        c = re.sub(r"[^0-9a-zA-Z_]+", "_", c)
        c = re.sub(r"_+", "_", c).strip("_")
        return c or "col"
    cleaned = [_clean(c) for c in cols]
    # make unique
    seen = {}
    out = []
    for c in cleaned:
        if c not in seen:
            seen[c] = 0
            out.append(c)
        else:
            seen[c] += 1
            out.append(f"{c}_{seen[c]}")
    return out


def coerce_datetimes(df: pd.DataFrame) -> pd.DataFrame:
    dateish = [c for c in df.columns if c.lower() in ("date", "time", "timestamp", "datetime")]
    for c in dateish:
        try:
            df[c] = pd.to_datetime(df[c], errors="coerce")
        except Exception:
            pass
    return df


def read_one_csv(
    file_like,
    *,
    encoding: Optional[str],
    sep: str,
    decimal: str,
    header_mode: str,
    na_values: List[str],
    auto_parse_dates: bool,
) -> pd.DataFrame:
    header = 0 if header_mode == "Row 1 has column names" else None
    df = pd.read_csv(
        file_like,
        encoding=encoding or None,
        sep=sep or ",",
        decimal=decimal or ".",
        header=header,
        na_values=na_values or None,
        keep_default_na=True,
        engine="python",  # tolerant with odd delimiters/encodings
    )
    # if no header, create generic names before standardizing
    if header is None:
        df.columns = [f"col_{i+1}" for i in range(df.shape[1])]
    df.columns = standardize_columns(df.columns.tolist())
    if auto_parse_dates:
        df = coerce_datetimes(df)
    return df


def align_union(dfs: List[pd.DataFrame]) -> pd.DataFrame:
    all_cols = sorted(set().union(*[set(d.columns) for d in dfs]))
    aligned = [d.reindex(columns=all_cols) for d in dfs]
    return pd.concat(aligned, ignore_index=True)


def align_intersection(dfs: List[pd.DataFrame]) -> pd.DataFrame:
    common = set(dfs[0].columns)
    for d in dfs[1:]:
        common &= set(d.columns)
    common = sorted(common)
    if not common:
        return pd.DataFrame()
    return pd.concat([d[common].copy() for d in dfs], ignore_index=True)


def safe_ensure_trailing_newline(path: str) -> None:
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return
    with open(path, "rb") as f:
        f.seek(-1, os.SEEK_END)
        last = f.read(1)
    if last not in (b"\n", b"\r"):
        with open(path, "ab") as f:
            f.write(b"\n")


def append_to_base_csv(
    base_path: str,
    df_to_append: pd.DataFrame,
    *,
    dedup_against_base: bool,
) -> Tuple[int, int]:
    """Append rows to base CSV. Returns (rows_before, rows_appended)."""
    rows_before = 0
    base_exists = os.path.exists(base_path)
    if base_exists and os.path.getsize(base_path) > 0:
        base = pd.read_csv(base_path, engine="python")
        base.columns = standardize_columns(base.columns.tolist())
        rows_before = len(base)
        # align columns for comparison and writing
        cols = sorted(set(base.columns) | set(df_to_append.columns))
        base = base.reindex(columns=cols)
        new_aligned = df_to_append.reindex(columns=cols)

        if dedup_against_base:
            # drop rows that already exist (exact row-wise duplicate across aligned cols)
            marker = pd.concat([base.assign(__is_base=True), new_aligned.assign(__is_base=False)], ignore_index=True)
            marker = marker.drop_duplicates(subset=cols, keep="first")
            dedup_new = marker[marker["__is_base"] == False].drop(columns="__is_base")  # noqa: E712
            new_aligned = dedup_new.reindex(columns=cols)

        # ensure newline to avoid row merges
        safe_ensure_trailing_newline(base_path)

        # append without header
        new_aligned.to_csv(base_path, mode="a", index=False, header=False)
        rows_appended = len(new_aligned)
        return rows_before, rows_appended
    else:
        # create new file with header
        df_to_append.to_csv(base_path, index=False)
        return 0, len(df_to_append)


# ---------------- UI: Read Options ----------------
with st.expander("⚙️ Read options", expanded=True):
    c1, c2, c3 = st.columns(3)
    encoding = c1.selectbox("Encoding", ["utf-8", "utf-16", "latin-1", "cp1252", "auto (leave blank)"], index=0)
    encoding = None if encoding.startswith("auto") else encoding

    delimiter = c2.text_input("Delimiter (sep)", value=",", help="Common: ,  ;  |  \\t")
    decimal = c3.text_input("Decimal symbol", value=".", help="Use , for European decimals.")

    header_mode = st.radio(
        "Header",
        ["Row 1 has column names", "No header (create generic)"],
        horizontal=True,
        index=0,
    )

    na_str = st.text_input("Extra NA values (comma-separated)", value="", help="e.g., NA, N/A, null, -9999")
    na_values = [s.strip() for s in na_str.split(",") if s.strip()] if na_str else []

    auto_parse_dates = st.checkbox("Auto-parse datelike columns (Date, Time, Timestamp, Datetime)", value=True)

with st.expander("🧼 Standardization & Merge", expanded=True):
    add_src = st.checkbox("Add source filename column", value=True)
    src_col = st.text_input("Source column name", value="source_file")
    within_dedup = st.checkbox("De-duplicate within each uploaded file", value=False)
    combine_mode = st.radio("Combine uploads by", ["Union of columns", "Intersection of columns"], horizontal=True)

# ---------------- Upload ----------------
uploaded_files = st.file_uploader("Upload one or more CSV files", type=["csv"], accept_multiple_files=True)

dfs: List[pd.DataFrame] = []
names: List[str] = []

if uploaded_files:
    for f in uploaded_files:
        try:
            df_one = read_one_csv(
                f, encoding=encoding, sep=delimiter, decimal=decimal,
                header_mode=header_mode, na_values=na_values, auto_parse_dates=auto_parse_dates
            )
            if within_dedup:
                df_one = df_one.drop_duplicates().reset_index(drop=True)
            if add_src:
                # ensure string for filename; UploadedFile has .name
                df_one[src_col] = getattr(f, "name", "upload.csv")
            dfs.append(df_one)
            names.append(getattr(f, "name", "upload.csv"))
        except Exception as e:
            st.error(f"Failed to read '{getattr(f, 'name', 'upload.csv')}': {e}")

# ---------------- Previews ----------------
if dfs:
    st.subheader("📄 Previews")
    for i, (nm, d) in enumerate(zip(names, dfs), start=1):
        with st.expander(f"Preview {i}: {nm}  •  shape={d.shape}", expanded=False):
            st.dataframe(d.head(200), use_container_width=True)
else:
    st.info("Upload CSV files to begin.")
    st.stop()

# ---------------- Combine ----------------
st.subheader("🔗 Combine Uploads")
if len(dfs) == 1:
    combined = dfs[0].copy()
else:
    if combine_mode.startswith("Union"):
        combined = align_union(dfs)
    else:
        combined = align_intersection(dfs)

if combined.empty:
    st.warning("Combined result is empty (no common columns). Consider using 'Union of columns'.")
else:
    st.caption(f"Combined shape: **{combined.shape[0]:,} × {combined.shape[1]:,}**")
    st.dataframe(combined.head(300), use_container_width=True)

# ---------------- Download combined ----------------
csv_bytes = combined.to_csv(index=False).encode("utf-8")
st.download_button(
    "⬇️ Download combined CSV",
    data=csv_bytes,
    file_name="combined_upload.csv",
    mime="text/csv",
)

st.divider()

# ---------------- Append to Base CSV ----------------
st.subheader("➕ Append to Base CSV")
base_col1, base_col2 = st.columns([2, 1])
base_path = base_col1.text_input(
    "Base CSV path (will be created if not exists)",
    value="data/base.csv",
    help="Provide a writable path in your workspace."
)
dedup_against_base = base_col2.checkbox("De-duplicate against base before appending", value=True)

do_append = st.button("Append combined to base CSV", type="primary", disabled=combined.empty or not base_path)

if do_append:
    try:
        os.makedirs(os.path.dirname(base_path), exist_ok=True) if os.path.dirname(base_path) else None
        # Make sure base columns are standardized like uploads
        if os.path.exists(base_path) and os.path.getsize(base_path) > 0:
            base_df = pd.read_csv(base_path, engine="python")
            base_df.columns = standardize_columns(base_df.columns.tolist())
            # align combined to union of columns (keep upload schema)
            all_cols = sorted(set(base_df.columns) | set(combined.columns))
            base_df = base_df.reindex(columns=all_cols)
            combined_aligned = combined.reindex(columns=all_cols)
            # write back normalized header if file was messy
            base_df.to_csv(base_path, index=False)
            rows_before, rows_added = append_to_base_csv(base_path, combined_aligned, dedup_against_base=dedup_against_base)
        else:
            rows_before, rows_added = append_to_base_csv(base_path, combined, dedup_against_base=False)

        st.success(f"Appended {rows_added:,} rows to '{base_path}'. Base had {rows_before:,} rows.")
    except Exception as e:
        st.error(f"Append failed: {e}")

st.caption("✅ This page is standalone; no other files need changes.")
