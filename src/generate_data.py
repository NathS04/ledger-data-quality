"""Generate synthetic accounts-payable data with planted quality issues."""
import os
import random

import numpy as np
import pandas as pd

RAW_DIR = os.path.join("data", "raw")
SEED = 42


def _money(value):
    formats = [
        lambda x: f"£{x:,.2f}",
        lambda x: f"{x:,.2f}",
        lambda x: f"{x:.2f}",
        lambda x: f"{x}",
    ]
    return random.choice(formats)(value)


def _date(value):
    return value.strftime(random.choice(["%Y-%m-%d", "%d/%m/%Y", "%d %b %Y", "%m/%d/%Y"]))


def generate(n_vendors=200, n_txns=10000):
    random.seed(SEED)
    np.random.seed(SEED)
    os.makedirs(RAW_DIR, exist_ok=True)
    categories = ["IT", "Facilities", "Travel", "Marketing", "Logistics", "Consulting"]
    names = ["Acme", "Globex", "Initech", "Umbrella", "Soylent", "Stark", "Wayne", "Hooli"]
    suffixes = ["Ltd", "LLP", "Group", "Services", "Holdings", "Partners"]
    vendors = pd.DataFrame(
        {
            "vendor_id": [f"V{i:04d}" for i in range(1, n_vendors + 1)],
            "vendor_name": [
                f"{random.choice(names)} {random.choice(suffixes)} {i}"
                for i in range(1, n_vendors + 1)
            ],
            "category": [random.choice(categories) for _ in range(n_vendors)],
        }
    )

    start = pd.Timestamp("2024-01-01")
    rows = []
    for i in range(1, n_txns + 1):
        vendor = random.randint(1, n_vendors)
        rows.append(
            {
                "transaction_id": f"T{i:06d}",
                "vendor_id": f"V{vendor:04d}",
                "invoice_number": f"INV-{random.randint(10000, 99999)}",
                "txn_date": start + pd.Timedelta(days=random.randint(0, 540)),
                "amount": round(np.random.lognormal(6, 1.1), 2),
                "currency": "GBP",
                "gl_account": random.choice(["6000", "6100", "6200", "6300", "6400", "6500"]),
                "description": random.choice(
                    ["Software licence", "Office supplies", "Air travel", "Ad spend", "Freight", "Advisory fee"]
                ),
            }
        )

    transactions = pd.DataFrame(rows)
    control = transactions.groupby("gl_account")["amount"].sum().round(2).reset_index()
    control.columns = ["gl_account", "control_total"]

    duplicates = transactions.sample(150, random_state=SEED).copy()
    duplicates["transaction_id"] = [f"T9{i:05d}" for i in range(len(duplicates))]
    duplicates["txn_date"] += pd.to_timedelta(np.random.randint(0, 4, len(duplicates)), unit="D")
    transactions = pd.concat([transactions, duplicates], ignore_index=True)

    orphan_index = transactions.sample(80, random_state=1).index
    transactions.loc[orphan_index, "vendor_id"] = [f"V9{random.randint(100, 999)}" for _ in range(80)]
    for column, count, seed in [("amount", 60, 11), ("vendor_id", 40, 12), ("txn_date", 30, 13)]:
        transactions.loc[transactions.sample(count, random_state=seed).index, column] = np.nan
    anomaly_index = transactions.sample(120, random_state=7).index
    transactions.loc[anomaly_index, "amount"] = [
        random.choice([9000, 9500, 9999, 90000, 95000]) for _ in range(120)
    ]

    output = transactions.copy()
    output["txn_date"] = output["txn_date"].apply(lambda d: _date(d) if pd.notna(d) else "")
    output["amount"] = output["amount"].apply(lambda a: _money(a) if pd.notna(a) else "")
    vendor_output = vendors.copy()
    noisy_index = vendor_output.sample(frac=0.3, random_state=3).index
    vendor_output.loc[noisy_index, "vendor_name"] = vendor_output.loc[noisy_index, "vendor_name"].apply(
        lambda value: random.choice([value.upper(), f"  {value} ", value.lower()])
    )

    midpoint = len(output) // 2
    output.iloc[:midpoint].to_csv(f"{RAW_DIR}/transactions_2024_h1.csv", index=False)
    output.iloc[midpoint : midpoint + midpoint // 2].to_csv(
        f"{RAW_DIR}/transactions_2024_h2.csv", index=False
    )
    output.iloc[midpoint + midpoint // 2 :].to_excel(f"{RAW_DIR}/transactions_2025.xlsx", index=False)
    vendor_output.to_csv(f"{RAW_DIR}/vendors.csv", index=False)
    control.to_csv(f"{RAW_DIR}/control_totals.csv", index=False)
    print(f"Generated {len(output)} transactions, {len(vendors)} vendors -> {RAW_DIR}/")


if __name__ == "__main__":
    generate()
