# settings/constants.py

"""
Global constants used across the HR Leave Management App.
This module contains static values and configuration shared across modules.
"""

import datetime
import streamlit as st

# ---------------------------------------------------
# Application metadata
# ---------------------------------------------------
APP_TITLE = "HR Leave Management"
APP_VERSION = "2.0"

# ---------------------------------------------------
# Environment configuration
# ---------------------------------------------------
# Read secrets ONCE here, so utils/db.py and utils/auth.py can import them.
SUPABASE_URL = st.secrets["SUPABASE_URL"]
API_KEY = st.secrets["SUPABASE_ANON_KEY"]

# ---------------------------------------------------
# Supported years for vacation logic
# ---------------------------------------------------
SUPPORTED_YEARS = [2025, 2026]

# ---------------------------------------------------
# Table Names
# ---------------------------------------------------
TABLE_DIPENDENTI = "dipendenti"
TABLE_RICHIESTE = "richieste_ferie"

# ---------------------------------------------------
# Holidays (used in charts + optional future business logic)
# ---------------------------------------------------
HOLIDAYS_FIXED = {
    datetime.date(2025, 12, 8),
    datetime.date(2025, 12, 25),
    datetime.date(2025, 12, 26),
    datetime.date(2026, 1, 1),
    datetime.date(2026, 1, 6),
}
