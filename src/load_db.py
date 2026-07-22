"""Load cleaned data into SQLite via SQLAlchemy."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
from sqlalchemy import Column, Float, MetaData, String, Table, create_engine, text

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "processed" / "ledger.db"


def get_engine(db_path: Path | None = None):
    db_path = db_path or DEFAULT_DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{db_path}")


def create_schema(engine) -> None:
    metadata = MetaData()

    Table(
        "vendors",
        metadata,
        Column("vendor_id", String, primary_key=True),
        Column("vendor_name", String),
        Column("country", String),
    )

    Table(
        "transactions",
        metadata,
        Column("transaction_id", String),
        Column("vendor_id", String),
        Column("vendor_name", String),
        Column("transaction_date", String),
        Column("amount", Float),
        Column("currency", String),
        Column("account_code", String),
        Column("description", String),
        Column("source_file", String),
    )

    metadata.create_all(engine)


def load_data(
    transactions: pd.DataFrame,
    vendors: pd.DataFrame,
    db_path: Path | None = None,
) -> Path:
    """Create schema and load cleaned frames into SQLite."""
    db_path = db_path or DEFAULT_DB_PATH
    engine = get_engine(db_path)

    vendor_cols = ["vendor_id", "vendor_name", "country"]
    txn_cols = [
        "transaction_id",
        "vendor_id",
        "vendor_name",
        "transaction_date",
        "amount",
        "currency",
        "account_code",
        "description",
        "source_file",
    ]

    vendors_load = vendors[[c for c in vendor_cols if c in vendors.columns]]
    txn_load = transactions[[c for c in txn_cols if c in transactions.columns]]

    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS transactions"))
        conn.execute(text("DROP TABLE IF EXISTS vendors"))
    create_schema(engine)

    if not vendors_load.empty:
        vendors_load.to_sql("vendors", engine, if_exists="append", index=False)
    txn_load.to_sql("transactions", engine, if_exists="append", index=False)

    with engine.connect() as conn:
        txn_count = conn.execute(text("SELECT COUNT(*) FROM transactions")).scalar()
        vnd_count = conn.execute(text("SELECT COUNT(*) FROM vendors")).scalar()

    logger.info("Loaded %d transactions and %d vendors into %s", txn_count, vnd_count, db_path)
    return db_path
