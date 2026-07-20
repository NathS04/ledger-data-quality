"""Automated data-quality checks: completeness, uniqueness, referential integrity, reconciliation."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

CRITICAL_COLUMNS = ["transaction_id", "vendor_id", "vendor_name", "transaction_date", "amount"]
COMPLETENESS_THRESHOLD = 0.95


def _result(passed: bool, details: str, flagged_rows: pd.DataFrame | None = None) -> dict:
    return {
        "passed": passed,
        "details": details,
        "flagged_rows": flagged_rows if flagged_rows is not None else pd.DataFrame(),
    }


def check_completeness(transactions: pd.DataFrame, threshold: float = COMPLETENESS_THRESHOLD) -> dict:
    """Flag rows missing critical fields; fail if any column below threshold."""
    present_cols = [c for c in CRITICAL_COLUMNS if c in transactions.columns]
    pct_by_col = {}
    flagged_parts = []

    for col in present_cols:
        non_null_pct = transactions[col].notna().mean()
        pct_by_col[col] = round(non_null_pct * 100, 2)
        missing = transactions[transactions[col].isna()].copy()
        if not missing.empty:
            missing = missing.assign(_issue_type="completeness", _issue_reason=f"Missing {col}")
            flagged_parts.append(missing)

    flagged = pd.concat(flagged_parts, ignore_index=True) if flagged_parts else pd.DataFrame()
    min_pct = min(pct_by_col.values()) if pct_by_col else 100.0
    passed = min_pct >= threshold * 100
    details = "; ".join(f"{k}: {v}%" for k, v in pct_by_col.items())
    return _result(passed, f"Completeness — {details} (threshold {threshold*100:.0f}%)", flagged)


def check_uniqueness(transactions: pd.DataFrame) -> dict:
    """Detect duplicate transaction IDs."""
    if "transaction_id" not in transactions.columns:
        return _result(False, "transaction_id column missing", pd.DataFrame())

    dup_mask = transactions.duplicated(subset=["transaction_id"], keep=False)
    flagged = transactions[dup_mask].copy()
    if not flagged.empty:
        flagged["_issue_type"] = "uniqueness"
        flagged["_issue_reason"] = "Duplicate transaction_id"

    dup_count = transactions.duplicated(subset=["transaction_id"], keep=False).sum()
    passed = dup_count == 0
    details = f"Found {dup_count} rows with duplicate transaction_id values"
    return _result(passed, details, flagged)


def check_referential_integrity(transactions: pd.DataFrame, vendors: pd.DataFrame) -> dict:
    """Flag transactions whose vendor_id is not in vendors table."""
    if vendors.empty or "vendor_id" not in transactions.columns:
        return _result(False, "Vendors table empty or vendor_id missing", pd.DataFrame())

    valid_ids = set(vendors["vendor_id"].astype(str))
    txn_vendor = transactions["vendor_id"].astype(str)
    orphan_mask = ~txn_vendor.isin(valid_ids) & txn_vendor.notna()
    flagged = transactions[orphan_mask].copy()
    if not flagged.empty:
        flagged["_issue_type"] = "referential_integrity"
        flagged["_issue_reason"] = "vendor_id not found in vendors table"

    count = orphan_mask.sum()
    passed = count == 0
    details = f"{count} transactions reference unknown vendor_id"
    return _result(passed, details, flagged)


def check_reconciliation(
    transactions: pd.DataFrame,
    tolerance: float = 0.01,
    control_path: Path | None = None,
) -> dict:
    """
    Sum transaction amounts by period and compare to control totals.
    Flags period-level variances exceeding tolerance (absolute £).
    """
    control_path = control_path or PROCESSED_DIR / "period_control_totals.csv"
    if not control_path.exists():
        return _result(False, f"Control totals file not found: {control_path}", pd.DataFrame())

    if "amount" not in transactions.columns or "transaction_date" not in transactions.columns:
        return _result(False, "amount or transaction_date column missing", pd.DataFrame())

    valid = transactions.dropna(subset=["amount", "transaction_date"]).copy()
    valid["period"] = valid["transaction_date"].str[:7]
    actual = valid.groupby("period")["amount"].sum()

    control = pd.read_csv(control_path)
    control["period"] = control["period"].astype(str)
    control_map = dict(zip(control["period"], control["control_amount"]))

    flagged_rows = []
    variances = []
    for period, control_amt in control_map.items():
        actual_amt = actual.get(period, 0.0)
        variance = round(float(actual_amt) - float(control_amt), 2)
        variances.append((period, variance))
        if abs(variance) > tolerance:
            period_txns = valid[valid["period"] == period].copy()
            period_txns["_issue_type"] = "reconciliation"
            period_txns["_issue_reason"] = (
                f"Period {period} variance £{variance:,.2f} vs control £{control_amt:,.2f}"
            )
            flagged_rows.append(period_txns)

    flagged = pd.concat(flagged_rows, ignore_index=True) if flagged_rows else pd.DataFrame()
    failed_periods = [p for p, v in variances if abs(v) > tolerance]
    passed = len(failed_periods) == 0
    details = f"Reconciliation across {len(control_map)} periods; {len(failed_periods)} period(s) with variance > £{tolerance}"
    if variances:
        max_var = max(variances, key=lambda x: abs(x[1]))
        details += f"; max variance: {max_var[0]} £{max_var[1]:,.2f}"
    return _result(passed, details, flagged)


def run_all_checks(
    transactions: pd.DataFrame,
    vendors: pd.DataFrame,
) -> dict[str, dict]:
    return {
        "completeness": check_completeness(transactions),
        "uniqueness": check_uniqueness(transactions),
        "referential_integrity": check_referential_integrity(transactions, vendors),
        "reconciliation": check_reconciliation(transactions),
    }
