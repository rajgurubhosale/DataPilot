import streamlit as st
import pandas as pd
from dataanalyst_agent.frontend.api import send_data_to_backend

st.set_page_config(page_title="AutoAnalyst", page_icon="📊", layout="wide")
st.title("📊 AutoAnalyst")
st.caption("Upload a CSV and get instant insights.")

file = st.file_uploader("Upload your CSV file", type="csv", max_upload_size=25)

if st.button("Perform data analysis"):
    if file:
        with st.spinner("Analyzing..."):
            data = send_data_to_backend(file)
        if data:
            st.session_state["analysis"] = data
            st.switch_page("pages/basic_analysis.py")
    else:
        st.warning("Please upload a CSV file first.")


