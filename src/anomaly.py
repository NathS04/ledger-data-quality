"""Anomaly detection: duplicate payments and Benford's Law analysis."""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import chisquare

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUTS_DIR = PROJECT_ROOT / "outputs"

# Benford expected frequencies for digits 1-9
BENFORD_EXPECTED = np.log10(1 + 1 / np.arange(1, 10))
DATE_WINDOW_DAYS = 3
BENFORD_CHI_SQUARE_ALPHA = 0.05


def _leading_digit(amount: float) -> int | None:
    if pd.isna(amount) or amount == 0:
        return None
    text = f"{abs(amount):.2f}".lstrip("0").replace(".", "")
    if not text:
        return None
    return int(text[0])


def detect_duplicate_payments(
    transactions: pd.DataFrame,
    window_days: int = DATE_WINDOW_DAYS,
) -> dict:
    """
    Surface likely duplicate payments: same vendor + amount within a date window.
    """
    required = {"vendor_id", "amount", "transaction_date", "transaction_id"}
    if not required.issubset(transactions.columns):
        return {
            "passed": False,
            "details": "Missing columns for duplicate-payment detection",
            "flagged_rows": pd.DataFrame(),
        }

    df = transactions.dropna(subset=["vendor_id", "amount", "transaction_date"]).copy()
    df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
    df = df.dropna(subset=["transaction_date"])
    df = df.sort_values(["vendor_id", "amount", "transaction_date"])

    flagged_indices = set()
    groups = df.groupby(["vendor_id", "amount"])

    for (_, _), group in groups:
        if len(group) < 2:
            continue
        dates = group["transaction_date"].tolist()
        idxs = group.index.tolist()
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                delta = abs((dates[j] - dates[i]).days)
                if 0 < delta <= window_days:
                    flagged_indices.add(idxs[i])
                    flagged_indices.add(idxs[j])

    flagged = df.loc[sorted(flagged_indices)].copy()
    if not flagged.empty:
        flagged["transaction_date"] = flagged["transaction_date"].dt.strftime("%Y-%m-%d")
        flagged["_issue_type"] = "duplicate_payment"
        flagged["_issue_reason"] = (
            f"Same vendor + amount within {window_days}-day window (likely double payment)"
        )

    pair_count = len(flagged_indices)
    passed = pair_count == 0
    details = f"Flagged {pair_count} transaction row(s) as duplicate-payment candidates"
    return {"passed": passed, "details": details, "flagged_rows": flagged}


def benfords_law_test(
    transactions: pd.DataFrame,
    alpha: float = BENFORD_CHI_SQUARE_ALPHA,
    output_path: Path | None = None,
) -> dict:
    """
    Compare leading-digit distribution to Benford's Law.
    Returns chi-square statistic, p-value, and per-digit breakdown.
    """
    output_path = output_path or OUTPUTS_DIR / "benford.csv"
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    amounts = transactions["amount"].dropna()
    digits = amounts.map(_leading_digit).dropna().astype(int)
    digits = digits[(digits >= 1) & (digits <= 9)]

    if len(digits) < 50:
        return {
            "passed": True,
            "details": "Insufficient data for Benford test",
            "flagged_rows": pd.DataFrame(),
            "benford_df": pd.DataFrame(),
        }

    observed = np.array([(digits == d).sum() for d in range(1, 10)], dtype=float)
    expected = BENFORD_EXPECTED * observed.sum()
    chi2, p_value = chisquare(observed, expected)

    benford_df = pd.DataFrame(
        {
            "digit": range(1, 10),
            "actual_count": observed.astype(int),
            "actual_pct": (observed / observed.sum() * 100).round(2),
            "expected_pct": (BENFORD_EXPECTED * 100).round(2),
            "deviation_pct": ((observed / observed.sum() - BENFORD_EXPECTED) * 100).round(2),
        }
    )
    benford_df.to_csv(output_path, index=False)

    passed = p_value >= alpha
    details = (
        f"Benford chi-square={chi2:.2f}, p-value={p_value:.4f} "
        f"({'PASS' if passed else 'FAIL — distribution deviates from Benford'})"
    )

    flagged = pd.DataFrame()
    if not passed:
        # Flag transactions with leading digits 8 or 9 as contributors
        high_digit_mask = transactions["amount"].map(_leading_digit).isin([8, 9])
        flagged = transactions[high_digit_mask].copy()
        flagged["_issue_type"] = "benford_anomaly"
        flagged["_issue_reason"] = "Amount leading digit contributes to Benford deviation"

    return {
        "passed": passed,
        "details": details,
        "flagged_rows": flagged,
        "benford_df": benford_df,
        "chi2": chi2,
        "p_value": p_value,
    }


def run_anomaly_detection(transactions: pd.DataFrame) -> dict[str, dict]:
    return {
        "duplicate_payments": detect_duplicate_payments(transactions),
        "benford": benfords_law_test(transactions),
    }
