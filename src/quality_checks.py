"""Completeness, uniqueness, referential-integrity, and reconciliation checks."""
import pandas as pd

CRITICAL = ["transaction_id", "vendor_id", "txn_date", "amount"]


def check_completeness(frame, critical=CRITICAL):
    percentages = {column: round(100 * frame[column].notna().mean(), 2) for column in critical}
    flagged = frame[frame[critical].isna().any(axis=1)].copy()
    flagged["__issue"] = "missing_critical_field"
    return {
        "check": "completeness",
        "passed": flagged.empty,
        "completeness_pct": percentages,
        "n_flagged": len(flagged),
        "rows": flagged,
    }


def check_uniqueness(frame, key="transaction_id"):
    mask = frame.duplicated(subset=key, keep=False) & frame[key].notna()
    flagged = frame[mask].copy()
    flagged["__issue"] = "duplicate_transaction_id"
    return {"check": "uniqueness", "passed": flagged.empty, "n_flagged": len(flagged), "rows": flagged}


def check_referential_integrity(transactions, vendors):
    valid = set(vendors["vendor_id"].dropna())
    mask = ~transactions["vendor_id"].isin(valid) & transactions["vendor_id"].notna()
    flagged = transactions[mask].copy()
    flagged["__issue"] = "orphan_vendor_id"
    return {
        "check": "referential_integrity",
        "passed": flagged.empty,
        "n_flagged": len(flagged),
        "rows": flagged,
    }


def check_reconciliation(transactions, control, tolerance=0.01):
    actual = transactions.groupby("gl_account")["amount"].sum().round(2)
    expected = control.set_index("gl_account")["control_total"].round(2)
    reconciliation = pd.DataFrame({"control_total": expected, "actual_total": actual}).fillna(0.0)
    reconciliation["variance"] = (
        reconciliation["actual_total"] - reconciliation["control_total"]
    ).round(2)
    reconciliation["reconciled"] = reconciliation["variance"].abs() <= tolerance
    breaks = reconciliation[~reconciliation["reconciled"]].reset_index()
    return {
        "check": "reconciliation",
        "passed": bool(reconciliation["reconciled"].all()),
        "n_breaks": len(breaks),
        "detail": reconciliation.reset_index(),
        "rows": breaks,
    }
