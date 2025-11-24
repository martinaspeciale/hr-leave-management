import streamlit as st
import requests

from settings.constants import SUPABASE_URL, API_KEY

def get_auth_headers():
    token = st.session_state.get("access_token")
    if not token:
        return None
    return {
        "apikey": API_KEY,
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

def login(email, password):
    url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
    headers = {
        "apikey": API_KEY,
        "Content-Type": "application/json",
    }
    r = requests.post(url, headers=headers, json={"email": email, "password": password})
    if r.status_code == 200:
        data = r.json()
        st.session_state["access_token"] = data["access_token"]
        st.session_state["user_email"] = data["user"]["email"]
        return True
    else:
        st.error(f"❌ Login fallito: {r.text}")
        return False

def logout():
    st.session_state.pop("access_token", None)
    st.session_state.pop("user_email", None)
