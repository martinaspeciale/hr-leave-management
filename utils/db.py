# utils/db.py

"""
Supabase database utilities:
CRUD operations (fetch, insert, update, delete)
and helper wrappers.
"""

import requests
import pandas as pd
from utils.auth import get_auth_headers
from settings.constants import SUPABASE_URL


def fetch_table(table: str) -> pd.DataFrame:
    """
    Generic fetch for any Supabase table.
    Returns DataFrame or empty DF.
    """
    headers = get_auth_headers()
    if not headers:
        return pd.DataFrame()

    url = f"{SUPABASE_URL}/rest/v1/{table}?select=*"
    r = requests.get(url, headers=headers)

    if r.status_code != 200:
        return pd.DataFrame()

    try:
        return pd.DataFrame(r.json())
    except Exception:
        return pd.DataFrame()


def db_insert(table: str, payload: dict) -> requests.Response:
    """POST insert row."""
    headers = get_auth_headers()
    return requests.post(f"{SUPABASE_URL}/rest/v1/{table}", headers=headers, json=payload)


def db_update(table: str, where: str, payload: dict) -> requests.Response:
    """PATCH update row(s). Example: where='id=eq.123'"""
    headers = get_auth_headers()
    url = f"{SUPABASE_URL}/rest/v1/{table}?{where}"
    return requests.patch(url, headers=headers, json=payload)


def db_delete(table: str, where: str) -> requests.Response:
    """DELETE row(s)."""
    headers = get_auth_headers()
    url = f"{SUPABASE_URL}/rest/v1/{table}?{where}"
    return requests.delete(url, headers=headers)
