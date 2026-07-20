"""Generate synthetic messy accounts-payable / general-ledger data with injected quality issues."""

from __future__ import annotations

import random
import string
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"

VENDORS = [
    ("V001", "Acme Supplies Ltd"),
    ("V002", "Global Tech Solutions"),
    ("V003", "Northern Logistics Co"),
    ("V004", "Premier Office Services"),
    ("V005", "City Utilities PLC"),
    ("V006", "DataStream Analytics"),
    ("V007", "Greenfield Consulting"),
    ("V008", "Metro Catering Group"),
    ("V009", "SecureNet IT Services"),
    ("V010", "Summit Facilities Mgmt"),
    ("V011", "BrightPrint Media"),
    ("V012", "Harbour Freight Ltd"),
    ("V013", "Atlas Software Inc"),
    ("V014", "Sterling Legal Partners"),
    ("V015", "Pioneer Health Supplies"),
]

ACCOUNTS = [
    "6100-Office Supplies",
    "6200-IT Equipment",
    "6300-Professional Services",
    "6400-Utilities",
    "6500-Travel & Entertainment",
    "6600-Maintenance",
    "6700-Marketing",
    "6800-Insurance",
]

DATE_FORMATS = [
    lambda d: d.strftime("%Y-%m-%d"),
    lambda d: d.strftime("%d/%m/%Y"),
    lambda d: d.strftime("%-d %b %Y") if hasattr(d, "strftime") else d.strftime("%d %b %Y"),
]

AMOUNT_FORMATTERS = [
    lambda a: f"£{a:,.2f}",
    lambda a: f"{a:.2f}",
    lambda a: f"{a:,.0f}",
    lambda a: str(int(a)) if a == int(a) else str(a),
]

VENDOR_NAME_VARIANTS = {
    "Acme Supplies Ltd": ["acme supplies ltd", "ACME SUPPLIES LTD", " Acme Supplies Ltd "],
    "Global Tech Solutions": ["global tech solutions", "GLOBAL TECH SOLUTIONS", " Global Tech Solutions "],
    "Northern Logistics Co": ["northern logistics co", "NORTHERN LOGISTICS CO", " Northern Logistics Co "],
}


def _random_date(start: datetime, end: datetime) -> datetime:
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def _format_date_messy(dt: datetime) -> str:
    fmt = random.choice(DATE_FORMATS)
    try:
        return fmt(dt)
    except ValueError:
        return dt.strftime("%d %b %Y")


def _format_amount_messy(amount: float) -> str:
    return random.choice(AMOUNT_FORMATTERS)(amount)


def _messy_vendor_name(clean_name: str) -> str:
    for key, variants in VENDOR_NAME_VARIANTS.items():
        if key == clean_name and random.random() < 0.4:
            return random.choice(variants)
    if random.random() < 0.15:
        return clean_name.upper()
    if random.random() < 0.1:
        return f" {clean_name} "
    return clean_name


def generate_vendors() -> pd.DataFrame:
    return pd.DataFrame(
        [{"vendor_id": vid, "vendor_name": name, "country": random.choice(["UK", "IE", "US"])} for vid, name in VENDORS]
    )


def generate_transactions(n: int = 10_000, seed: int = 42) -> tuple[pd.DataFrame, dict]:
    """Return transactions DataFrame and metadata including control totals."""
    random.seed(seed)
    np.random.seed(seed)

    start = datetime(2024, 1, 1)
    end = datetime(2025, 6, 30)
    vendor_ids = [v[0] for v in VENDORS]
    vendor_map = {v[0]: v[1] for v in VENDORS}

    rows: list[dict] = []
    for i in range(1, n + 1):
        vid = random.choice(vendor_ids)
        amount = round(abs(np.random.lognormal(mean=6.5, sigma=1.2)), 2)
        if amount < 10:
            amount = round(amount + 10, 2)
        txn_date = _random_date(start, end)
        rows.append(
            {
                "transaction_id": f"TXN-{i:06d}",
                "vendor_id": vid,
                "vendor_name": _messy_vendor_name(vendor_map[vid]),
                "transaction_date": _format_date_messy(txn_date),
                "amount": _format_amount_messy(amount),
                "currency": random.choice(["GBP", "GBP", "GBP", "EUR"]),
                "account_code": random.choice(ACCOUNTS),
                "description": f"Invoice payment {i}",
                "_amount_numeric": amount,
                "_date_iso": txn_date.strftime("%Y-%m-%d"),
            }
        )

    df = pd.DataFrame(rows)
    control_total = df["_amount_numeric"].sum()
    period_totals = df.groupby(df["_date_iso"].str[:7])["_amount_numeric"].sum().to_dict()

    meta = {"control_total": control_total, "period_totals": period_totals, "seed": seed}
    return df, meta


def inject_issues(df: pd.DataFrame, meta: dict) -> pd.DataFrame:
    """Inject data-quality problems into the transaction export."""
    df = df.copy()

    # Missing critical fields (~2%)
    missing_idx = df.sample(frac=0.02, random_state=1).index
    for idx in missing_idx:
        col = random.choice(["vendor_name", "transaction_date", "amount"])
        df.at[idx, col] = np.nan

    # Exact duplicate rows (~50 rows)
    dupes = df.sample(n=50, random_state=2).copy()
    df = pd.concat([df, dupes], ignore_index=True)

    # Duplicate transaction IDs (~30)
    dup_id_idx = df.sample(n=30, random_state=3).index
    existing_ids = df["transaction_id"].drop_duplicates().sample(n=30, random_state=4).tolist()
    for idx, new_id in zip(dup_id_idx, existing_ids):
        df.at[idx, "transaction_id"] = new_id

    # Near-duplicate payments: same vendor + amount within 3 days (~40 pairs)
    for _ in range(40):
        row = df.sample(n=1, random_state=random.randint(0, 9999)).iloc[0]
        if pd.isna(row.get("_amount_numeric")):
            continue
        new_row = row.copy()
        new_row["transaction_id"] = f"TXN-DUP-{random.randint(100000, 999999)}"
        base_date = datetime.strptime(row["_date_iso"], "%Y-%m-%d")
        offset = random.randint(1, 3)
        new_row["transaction_date"] = _format_date_messy(base_date + timedelta(days=offset))
        new_row["_date_iso"] = (base_date + timedelta(days=offset)).strftime("%Y-%m-%d")
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    # Referential breaks (~25 rows with invalid vendor_id)
    bad_idx = df.sample(n=25, random_state=5).index
    for idx in bad_idx:
        df.at[idx, "vendor_id"] = f"V{random.randint(900, 999):03d}"

    # Benford deviation: inflate amounts starting with 8 or 9 (~8% of rows)
    benford_idx = df.sample(frac=0.08, random_state=6).index
    for idx in benford_idx:
        if pd.notna(df.at[idx, "_amount_numeric"]):
            inflated = float(str(int(random.uniform(800, 9999))) + "." + f"{random.randint(0, 99):02d}")
            df.at[idx, "amount"] = _format_amount_messy(inflated)
            df.at[idx, "_amount_numeric"] = inflated

    # Drop internal columns before export (keep in meta for reconciliation)
    export_df = df.drop(columns=["_amount_numeric", "_date_iso"], errors="ignore")
    meta["row_count_after_injection"] = len(export_df)
    return export_df


def write_raw_files(transactions: pd.DataFrame, vendors: pd.DataFrame) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    # Split transactions across disjoint CSV, XLSX, and legacy exports (no overlap)
    n = len(transactions)
    split_a = int(n * 0.50)
    split_b = int(n * 0.85)
    part_a = transactions.iloc[:split_a].copy()
    part_b = transactions.iloc[split_a:split_b].copy()
    part_c = transactions.iloc[split_b:].copy()

    part_a.to_csv(RAW_DIR / "gl_export_batch1.csv", index=False)
    part_b.to_excel(RAW_DIR / "gl_export_batch2.xlsx", index=False, engine="openpyxl")

    # Legacy CSV with alternate column naming (disjoint rows)
    legacy = part_c.copy()
    legacy = legacy.rename(
        columns={
            "transaction_id": "Txn ID",
            "vendor_id": "Vendor Code",
            "vendor_name": "Vendor Name",
            "transaction_date": "Date",
            "amount": "Amount",
            "currency": "Curr",
            "account_code": "GL Account",
            "description": "Narrative",
        }
    )
    legacy.to_csv(RAW_DIR / "legacy_ap_export.csv", index=False)

    vendors.to_csv(RAW_DIR / "vendors.csv", index=False)
    vendors.to_excel(RAW_DIR / "vendors.xlsx", index=False, engine="openpyxl")


def save_control_metadata(meta: dict) -> None:
    processed = PROJECT_ROOT / "data" / "processed"
    processed.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [{"metric": "control_total", "value": meta["control_total"]}]
    ).to_csv(processed / "control_totals.csv", index=False)
    pd.DataFrame(
        [{"period": k, "control_amount": v} for k, v in sorted(meta["period_totals"].items())]
    ).to_csv(processed / "period_control_totals.csv", index=False)


def main() -> None:
    print("Generating synthetic ledger data...")
    vendors = generate_vendors()
    transactions, meta = generate_transactions(n=10_000, seed=42)
    messy = inject_issues(transactions, meta)
    write_raw_files(messy, vendors)
    save_control_metadata(meta)
    print(f"  Vendors: {len(vendors)}")
    print(f"  Transactions (with injected issues): {len(messy)}")
    print(f"  Control total: £{meta['control_total']:,.2f}")
    print(f"  Raw files written to {RAW_DIR}")


if __name__ == "__main__":
    main()
