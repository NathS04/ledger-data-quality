"""Load raw transaction exports, the vendor master, and control totals."""
import glob
import os

import pandas as pd

RAW_DIR = os.path.join("data", "raw")


def load_transactions():
    frames = []
    for path in sorted(glob.glob(f"{RAW_DIR}/transactions_*")):
        frame = pd.read_excel(path, dtype=str) if path.endswith(".xlsx") else pd.read_csv(path, dtype=str)
        frame["__source_file"] = os.path.basename(path)
        frames.append(frame)
        print(f"  read {len(frame):>6} rows from {os.path.basename(path)}")
    if not frames:
        raise FileNotFoundError(f"No transaction exports found under {RAW_DIR}")
    transactions = pd.concat(frames, ignore_index=True)
    print(f"  total ingested: {len(transactions)}")
    return transactions


def load_vendors():
    return pd.read_csv(f"{RAW_DIR}/vendors.csv", dtype=str)


def load_control_totals():
    return pd.read_csv(f"{RAW_DIR}/control_totals.csv", dtype={"gl_account": str})
