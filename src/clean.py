"""Standardise and clean ingested transaction and vendor data."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

CRITICAL_COLUMNS = ["transaction_id", "vendor_id", "vendor_name", "transaction_date", "amount"]


def standardize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    return df


def parse_dates(series: pd.Series) -> pd.Series:
    """Parse heterogeneous date strings to ISO YYYY-MM-DD."""

    def _parse_one(val):
        if pd.isna(val) or str(val).strip() == "":
            return pd.NA
        text = str(val).strip()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y", "%d %b %Y", "%d %B %Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        parsed = pd.to_datetime(text, dayfirst=True, errors="coerce")
        if pd.isna(parsed):
            return pd.NA
        return parsed.strftime("%Y-%m-%d")

    return series.map(_parse_one)


def parse_amounts(series: pd.Series) -> pd.Series:
    """Strip currency symbols, commas, and whitespace; coerce to float."""

    def _parse_one(val):
        if pd.isna(val) or str(val).strip() == "":
            return pd.NA
        text = str(val).strip()
        text = re.sub(r"[£$€,\s]", "", text)
        text = text.replace("(", "-").replace(")", "")
        try:
            return float(text)
        except ValueError:
            return pd.NA

    return series.map(_parse_one)


def normalize_vendor_names(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.lower().str.replace(r"\s+", " ", regex=True)


def clean_transactions(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Clean transaction data and return summary statistics."""
    summary: dict = {"rows_in": len(df), "exact_duplicates_removed": 0, "issues_fixed": []}
    df = standardize_column_names(df)

    if "transaction_date" in df.columns:
        before_null_dates = df["transaction_date"].isna().sum()
        df["transaction_date"] = parse_dates(df["transaction_date"])
        fixed_dates = before_null_dates - df["transaction_date"].isna().sum()
        if fixed_dates:
            summary["issues_fixed"].append(f"Parsed {fixed_dates} additional dates")

    if "amount" in df.columns:
        df["amount"] = parse_amounts(df["amount"])
        summary["issues_fixed"].append("Normalised amount formatting")

    if "vendor_name" in df.columns:
        df["vendor_name"] = normalize_vendor_names(df["vendor_name"])
        summary["issues_fixed"].append("Normalised vendor name casing/whitespace")

    for col in ("vendor_id", "transaction_id", "currency", "account_code"):
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            df[col] = df[col].replace({"nan": pd.NA, "None": pd.NA, "": pd.NA})

    # Remove exact duplicate rows (all columns except source_file)
    dedupe_cols = [c for c in df.columns if c != "source_file"]
    before = len(df)
    df = df.drop_duplicates(subset=dedupe_cols, keep="first")
    removed = before - len(df)
    summary["exact_duplicates_removed"] = removed
    if removed:
        summary["issues_fixed"].append(f"Removed {removed} exact duplicate rows")

    summary["rows_out"] = len(df)
    return df, summary


def clean_vendors(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = standardize_column_names(df)
    if "vendor_name" in df.columns:
        df["vendor_name"] = normalize_vendor_names(df["vendor_name"])
    if "vendor_id" in df.columns:
        df["vendor_id"] = df["vendor_id"].astype(str).str.strip()
    return df.drop_duplicates(subset=["vendor_id"], keep="first")


def write_processed(transactions: pd.DataFrame, vendors: pd.DataFrame) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    transactions.to_csv(PROCESSED_DIR / "transactions_clean.csv", index=False)
    if not vendors.empty:
        vendors.to_csv(PROCESSED_DIR / "vendors_clean.csv", index=False)


def clean(transactions: pd.DataFrame, vendors: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Full clean pipeline: standardise, dedupe, write processed files."""
    clean_txn, txn_summary = clean_transactions(transactions)
    clean_vnd = clean_vendors(vendors)
    write_processed(clean_txn, clean_vnd)
    summary = {"transactions": txn_summary, "vendors_out": len(clean_vnd)}
    logger.info(
        "Cleaned transactions: %d -> %d (removed %d duplicates)",
        txn_summary["rows_in"],
        txn_summary["rows_out"],
        txn_summary["exact_duplicates_removed"],
    )
    return clean_txn, clean_vnd, summary
