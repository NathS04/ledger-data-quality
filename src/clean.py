"""Standardise raw ledger data while retaining rows that checks should flag."""
import re
import warnings

import numpy as np
import pandas as pd


def _parse_amount(value):
    if value is None or (isinstance(value, float) and np.isnan(value)) or str(value).strip() == "":
        return np.nan
    text = str(value).strip()
    negative = text.startswith("(") and text.endswith(")")
    text = re.sub(r"[£$,()]", "", text)
    try:
        parsed = float(text)
        return -parsed if negative else parsed
    except ValueError:
        return np.nan


def _parse_date(value):
    if value is None or str(value).strip() == "":
        return pd.NaT
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return pd.to_datetime(str(value).strip(), dayfirst=True, errors="coerce")


def _clean_name(value):
    return value if pd.isna(value) else re.sub(r"\s+", " ", str(value)).strip().title()


def clean_transactions(frame):
    frame = frame.copy()
    frame.columns = [column.strip().lower() for column in frame.columns]
    frame["amount"] = frame["amount"].apply(_parse_amount)
    frame["txn_date"] = frame["txn_date"].apply(_parse_date)
    frame["vendor_id"] = frame["vendor_id"].astype("string").str.strip()
    frame["transaction_id"] = frame["transaction_id"].astype("string").str.strip()
    before = len(frame)
    frame = frame.drop_duplicates()
    summary = {
        "rows_in": before,
        "exact_duplicates_removed": before - len(frame),
        "rows_out": len(frame),
        "null_amount": int(frame["amount"].isna().sum()),
        "null_date": int(frame["txn_date"].isna().sum()),
        "null_vendor_id": int(frame["vendor_id"].isna().sum()),
    }
    return frame, summary


def clean_vendors(frame):
    frame = frame.copy()
    frame.columns = [column.strip().lower() for column in frame.columns]
    frame["vendor_id"] = frame["vendor_id"].astype("string").str.strip()
    frame["vendor_name"] = frame["vendor_name"].apply(_clean_name)
    return frame.drop_duplicates(subset="vendor_id")
