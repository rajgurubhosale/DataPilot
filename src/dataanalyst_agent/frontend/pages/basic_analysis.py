import streamlit as st
import pandas as pd

if "analysis" not in st.session_state:
    st.warning("Please upload a CSV file first.")
    st.page_link("app.py", label="⬅ Back to upload")
    st.stop()

col_nav1, col_nav2 = st.columns([1, 4])
col_nav1.page_link("app.py", label="⬅ Back to upload")
if "dashboard" in st.session_state:
    col_nav2.page_link("pages/dashboard.py", label="📊 Go to AI Dashboard")

data = st.session_state["analysis"]

c1, c2, c3 = st.columns(3)
c1.metric("Rows", f"{data['rows']:,}")
c2.metric("Columns", data["columns"])
c3.metric("Duplicates", data["duplicates"])

tab1, tab2, tab3 = st.tabs(["Preview", "Summary", "Profile"])

tab1.markdown("#### First few rows")
tab1.dataframe(pd.DataFrame(data["sample"]), use_container_width=True, height=400)

if not data["summary"]:
    tab2.info("No numeric columns found.")
else:
    tab2.markdown("### Descriptive Summary")
    summary_df = pd.DataFrame(data["summary"]).set_index("index")
    tab2.dataframe(summary_df, use_container_width=True)

profile_df = (
    pd.DataFrame(data["profile"])
    .set_index("column")
    .sort_values("missing", ascending=False)
)
tab3.dataframe(profile_df, use_container_width=True)