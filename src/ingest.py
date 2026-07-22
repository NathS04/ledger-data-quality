"""Load raw CSV and Excel exports from data/raw/."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"

# Canonical column mapping for heterogeneous exports
COLUMN_ALIASES = {
    "transaction_id": ["transaction_id", "txn id", "txn_id", "id"],
    "vendor_id": ["vendor_id", "vendor code", "vendor_code", "vendorid"],
    "vendor_name": ["vendor_name", "vendor name", "vendor"],
    "transaction_date": ["transaction_date", "date", "txn_date", "posting_date"],
    "amount": ["amount", "value", "txn_amount"],
    "currency": ["currency", "curr", "ccy"],
    "account_code": ["account_code", "gl account", "account", "gl_account"],
    "description": ["description", "narrative", "memo", "details"],
}


def _normalize_col(name: str) -> str:
    return str(name).strip().lower().replace("_", " ")


def _map_columns(df: pd.DataFrame) -> pd.DataFrame:
    col_lookup = {_normalize_col(c): c for c in df.columns}
    rename: dict[str, str] = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            key = _normalize_col(alias)
            if key in col_lookup:
                rename[col_lookup[key]] = canonical
                break
    return df.rename(columns=rename)


def _read_file(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path, dtype=str, keep_default_na=True)
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(path, dtype=str, engine="openpyxl")
    raise ValueError(f"Unsupported file type: {path.suffix}")


def ingest_raw(raw_dir: Path | None = None) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """
    Read all transaction and vendor files from raw_dir.

    Returns (transactions, vendors, ingest_log).
    """
    raw_dir = raw_dir or RAW_DIR
    ingest_log: dict = {"sources": [], "total_transaction_rows": 0}

    txn_frames: list[pd.DataFrame] = []
    vendor_frames: list[pd.DataFrame] = []

    for path in sorted(raw_dir.iterdir()):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".csv", ".xlsx", ".xls"}:
            continue

        df = _read_file(path)
        df["source_file"] = path.name

        if "vendor" in path.name.lower() and "transaction" not in path.name.lower():
            mapped = _map_columns(df)
            vendor_frames.append(mapped)
            ingest_log["sources"].append({"file": path.name, "type": "vendors", "rows": len(df)})
            logger.info("Ingested vendors from %s: %d rows", path.name, len(df))
        else:
            mapped = _map_columns(df)
            txn_frames.append(mapped)
            ingest_log["sources"].append({"file": path.name, "type": "transactions", "rows": len(df)})
            logger.info("Ingested transactions from %s: %d rows", path.name, len(df))

    if not txn_frames:
        raise FileNotFoundError(f"No transaction files found in {raw_dir}")

    transactions = pd.concat(txn_frames, ignore_index=True)
    ingest_log["total_transaction_rows"] = len(transactions)

    vendors = pd.concat(vendor_frames, ignore_index=True).drop_duplicates(subset=["vendor_id"]) if vendor_frames else pd.DataFrame()

    return transactions, vendors, ingest_log
