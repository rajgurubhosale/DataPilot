import streamlit as st
import pandas as pd

if "df" not in st.session_state:
    st.warning("Please upload a CSV file first.")
    st.page_link("app.py", label="⬅ Back to upload")
    st.stop()

df = st.session_state["df"]

c1, c2, c3,c4 = st.columns(4)
c1.metric("Rows", f"{len(df):,}")
c2.metric("Columns", df.shape[1])
c3.metric("Missing values", int(df.isna().sum().sum()))
c4.metric("duplicates",int(df.duplicated().sum()))
tab1, tab2, tab3 = st.tabs(["Preview", "Summary", "Profile"])

tab1.markdown("#### First few rows")
tab1.dataframe(df.head(10), use_container_width=True, height=400)

num_df = df.select_dtypes("number")
if num_df.empty:
    tab2.info("No numeric columns found.")
else:
    tab2.markdown("### Discriptive Summary")
    tab2.dataframe(num_df.describe().T, use_container_width=True)

profile = pd.DataFrame({
    "missing": df.isna().sum(),
    "missing_%": (df.isna().mean() * 100).round(1),
    "unique": df.nunique(),
}).sort_values("missing", ascending=False)

tab3.dataframe(profile, use_container_width=True)