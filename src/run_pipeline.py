"""Run the complete ledger data-quality and reconciliation pipeline."""
import os
import sys

import pandas as pd

from src import anomaly, clean, generate_data, ingest, load_db, quality_checks

OUT_DIR = "outputs"


def main(regenerate=True):
    os.makedirs(OUT_DIR, exist_ok=True)
    if regenerate or not os.path.exists("data/raw/vendors.csv"):
        print("Generating synthetic data...")
        generate_data.generate()

    print("Ingesting...")
    raw = ingest.load_transactions()
    vendors_raw = ingest.load_vendors()
    control = ingest.load_control_totals()

    print("Cleaning...")
    transactions, summary = clean.clean_transactions(raw)
    vendors = clean.clean_vendors(vendors_raw)
    print("  summary:", summary)

    print("Loading to SQLite...")
    load_db.load(transactions, vendors)

    print("Running quality checks...")
    results = [
        quality_checks.check_completeness(transactions),
        quality_checks.check_uniqueness(transactions),
        quality_checks.check_referential_integrity(transactions, vendors),
        quality_checks.check_reconciliation(transactions, control),
    ]
    duplicates = anomaly.detect_duplicate_payments(transactions)
    benford = anomaly.benford_test(transactions["amount"])

    frames = []
    for result in results:
        rows = result.get("rows")
        if rows is not None and len(rows):
            flagged = rows.copy()
            flagged["__check"] = result["check"]
            frames.append(flagged)
    if len(duplicates["rows"]):
        duplicate_rows = duplicates["rows"].copy()
        duplicate_rows["__check"] = "duplicate_payments"
        frames.append(duplicate_rows)
    exceptions = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    exceptions.to_csv(f"{OUT_DIR}/exceptions_report.csv", index=False)

    kpis = pd.DataFrame(
        [
            {
                "total_transactions": len(transactions),
                "total_spend": round(transactions["amount"].sum(), 2),
                "distinct_vendors": int(transactions["vendor_id"].nunique()),
                "missing_field_rows": results[0]["n_flagged"],
                "duplicate_ids": results[1]["n_flagged"],
                "orphan_vendor_rows": results[2]["n_flagged"],
                "reconciliation_breaks": results[3]["n_breaks"],
                "duplicate_payment_candidates": duplicates["n_flagged"],
                "benford_mad": benford["mad"],
                "benford_conformity": benford["conformity"],
            }
        ]
    )
    kpis.to_csv(f"{OUT_DIR}/kpis.csv", index=False)
    benford["table"].to_csv(f"{OUT_DIR}/benford.csv", index=False)
    results[3]["detail"].to_csv(f"{OUT_DIR}/reconciliation.csv", index=False)

    print("\n=== SUMMARY ===")
    for result in results:
        issue_count = result.get("n_flagged", result.get("n_breaks"))
        print(f"  [{'PASS' if result.get('passed') else 'FAIL'}] {result['check']}: {issue_count} issue(s)")
    print(f"  duplicate-payment candidates: {duplicates['n_flagged']}")
    print(
        f"  Benford MAD={benford['mad']} ({benford['conformity']}), "
        f"chi2={benford['chi_square']}"
    )
    print(f"  exceptions: {len(exceptions)} rows -> {OUT_DIR}/exceptions_report.csv")


if __name__ == "__main__":
    main(regenerate="--no-regen" not in sys.argv)
