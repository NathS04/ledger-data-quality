"""Load cleaned ledger data into SQLite."""
import os

from sqlalchemy import create_engine

DB_PATH = os.path.join("data", "processed", "ledger.db")


def load(transactions, vendors):
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    engine = create_engine(f"sqlite:///{DB_PATH}")
    vendors.to_sql("vendors", engine, if_exists="replace", index=False)
    transactions.to_sql("transactions", engine, if_exists="replace", index=False)
    print(f"  loaded {len(transactions)} txns + {len(vendors)} vendors -> {DB_PATH}")
    return engine
