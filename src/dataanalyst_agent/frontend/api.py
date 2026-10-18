import io
import requests
import streamlit as st
BACKEND_URL = "http://localhost:8000/"

def send_data_to_backend(file):

    files = {"file": (file.name, file.getvalue(), "text/csv")}

    try:
        response = requests.post(BACKEND_URL + "upload_data", files=files, timeout=30)
    except requests.exceptions.RequestException as e:
        st.error(f"Could not reach backend: {e}")
        return None
    if response.status_code != 200:
        st.error(f"API error {response.status_code}: {response.text}")
        return None 

    return response.json()