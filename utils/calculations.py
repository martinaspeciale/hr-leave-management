# utils/calculations.py

"""
Calculation utilities:
- vacation days per year (2025 / 2026)
- date expansion helpers
"""

from datetime import date
import pandas as pd

HOLIDAYS = {
    date(2025, 12, 8),
    date(2025, 12, 25),
    date(2025, 12, 26),
    date(2026, 1, 1),
    date(2026, 1, 6),
}

def is_working_day(d: date) -> bool:
    """Return True if the given date is NOT a weekend and NOT a holiday."""
    if d.weekday() >= 5:  # Saturday/Sunday
        return False
    if d in HOLIDAYS:
        return False
    return True


def calcola_giorni_2025_2026(data_inizio, data_fine):
    """
    Computes working-day counts for 2025 and 2026
    within a vacation request interval.
    """

    start = pd.to_datetime(data_inizio).date()
    end   = pd.to_datetime(data_fine).date()

    # Swap if needed
    if end < start:
        start, end = end, start

    # Boundaries
    y25_start = date(2025, 1, 1)
    y25_end   = date(2025, 12, 31)

    y26_start = date(2026, 1, 1)
    y26_end   = date(2026, 12, 31)

    # 2025 days
    s25 = max(start, y25_start)
    e25 = min(end, y25_end)
    giorni_2025 = max(0, (e25 - s25).days + 1)

    # 2026 days
    s26 = max(start, y26_start)
    e26 = min(end, y26_end)
    giorni_2026 = max(0, (e26 - s26).days + 1)

    return giorni_2025, giorni_2026
