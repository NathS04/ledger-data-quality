"""Orchestrate the full ledger data-quality pipeline."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
RAW_DIR = PROJECT_ROOT / "data" / "raw"

sys.path.insert(0, str(SRC_DIR))

from anomaly import run_anomaly_detection  # noqa: E402
from clean import clean  # noqa: E402
from ingest import ingest_raw  # noqa: E402
from load_db import load_data  # noqa: E402
from quality_checks import run_all_checks  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def ensure_raw_data() -> None:
    if not any(RAW_DIR.glob("*.csv")) and not any(RAW_DIR.glob("*.xlsx")):
        logger.info("No raw data found — generating synthetic dataset...")
        from generate_data import main as generate_main

        generate_main()


def build_exceptions_report(all_results: dict[str, dict]) -> pd.DataFrame:
    frames = []
    for check_name, result in all_results.items():
        flagged = result.get("flagged_rows", pd.DataFrame())
        if flagged is None or flagged.empty:
            continue
        df = flagged.copy()
        df["check_name"] = check_name
        if "_issue_type" not in df.columns:
            df["_issue_type"] = check_name
        if "_issue_reason" not in df.columns:
            df["_issue_reason"] = result.get("details", "")
        frames.append(df)

    if not frames:
        return pd.DataFrame(
            columns=[
                "check_name",
                "_issue_type",
                "_issue_reason",
                "transaction_id",
                "vendor_id",
                "amount",
            ]
        )

    report = pd.concat(frames, ignore_index=True)
    cols = ["check_name", "_issue_type", "_issue_reason"] + [
        c for c in report.columns if c not in {"check_name", "_issue_type", "_issue_reason"}
    ]
    return report[cols]


def build_kpis(
    transactions: pd.DataFrame,
    exceptions: pd.DataFrame,
    all_results: dict[str, dict],
) -> pd.DataFrame:
    valid_amounts = transactions["amount"].dropna()
    dup_candidates = all_results.get("duplicate_payments", {}).get("flagged_rows", pd.DataFrame())
    benford = all_results.get("benford", {})

    kpis = [
        ("total_spend", round(valid_amounts.sum(), 2)),
        ("transaction_count", len(transactions)),
        ("avg_transaction_amount", round(valid_amounts.mean(), 2) if len(valid_amounts) else 0),
        ("exception_count", len(exceptions)),
        ("duplicate_payment_candidates", len(dup_candidates) if dup_candidates is not None else 0),
        ("checks_passed", sum(1 for r in all_results.values() if r.get("passed"))),
        ("checks_failed", sum(1 for r in all_results.values() if not r.get("passed"))),
        ("benford_p_value", round(benford.get("p_value", 0), 4) if benford else None),
        ("benford_chi_square", round(benford.get("chi2", 0), 2) if benford else None),
    ]
    return pd.DataFrame(kpis, columns=["metric", "value"])


def print_summary(all_results: dict[str, dict], kpis: pd.DataFrame) -> None:
    print("\n" + "=" * 60)
    print("LEDGER DATA QUALITY PIPELINE — SUMMARY")
    print("=" * 60)
    for name, result in all_results.items():
        status = "PASS" if result["passed"] else "FAIL"
        print(f"  [{status}] {name}: {result['details']}")
    print("-" * 60)
    for _, row in kpis.iterrows():
        print(f"  {row['metric']}: {row['value']}")
    print("=" * 60 + "\n")


def run_pipeline() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    ensure_raw_data()

    logger.info("Step 1/5 — Ingesting raw files...")
    transactions, vendors, ingest_log = ingest_raw()
    logger.info("  Total rows ingested: %d from %d files", ingest_log["total_transaction_rows"], len(ingest_log["sources"]))

    logger.info("Step 2/5 — Cleaning and standardising...")
    clean_txn, clean_vnd, clean_summary = clean(transactions, vendors)

    logger.info("Step 3/5 — Loading into SQLite...")
    db_path = load_data(clean_txn, clean_vnd)
    logger.info("  Database: %s", db_path)

    logger.info("Step 4/5 — Running quality checks...")
    quality_results = run_all_checks(clean_txn, clean_vnd)

    logger.info("Step 5/5 — Running anomaly detection...")
    anomaly_results = run_anomaly_detection(clean_txn)

    all_results = {**quality_results, **anomaly_results}

    exceptions = build_exceptions_report(all_results)
    kpis = build_kpis(clean_txn, exceptions, all_results)

    exceptions.to_csv(OUTPUTS_DIR / "exceptions_report.csv", index=False)
    kpis.to_csv(OUTPUTS_DIR / "kpis.csv", index=False)

    # Benford CSV written by anomaly module; ensure it exists
    if "benford" in anomaly_results and anomaly_results["benford"].get("benford_df") is not None:
        anomaly_results["benford"]["benford_df"].to_csv(OUTPUTS_DIR / "benford.csv", index=False)

    print_summary(all_results, kpis)
    logger.info("Outputs written to %s", OUTPUTS_DIR)


if __name__ == "__main__":
    run_pipeline()
