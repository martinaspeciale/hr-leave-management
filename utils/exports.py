# utils/exports.py

"""
DataFrame export utilities:
Excel, CSV, JSON (UTF-8).
"""

import io
import pandas as pd


def df_to_excel_bytes(df: pd.DataFrame) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()


def df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def df_to_json_bytes(df: pd.DataFrame) -> bytes:
    s = df.to_json(orient="records", force_ascii=False, date_format="iso")
    return s.encode("utf-8")
