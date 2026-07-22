"""Duplicate-payment screening and Benford first-digit analysis."""
import numpy as np
import pandas as pd

BENFORD = {digit: np.log10(1 + 1 / digit) for digit in range(1, 10)}


def detect_duplicate_payments(frame):
    key = ["vendor_id", "invoice_number", "amount"]
    eligible = frame.dropna(subset=["vendor_id", "amount"]).copy()
    flagged = eligible[eligible.duplicated(subset=key, keep=False)].sort_values(key).copy()
    flagged["__issue"] = "duplicate_payment_candidate"
    return {"check": "duplicate_payments", "n_flagged": len(flagged), "rows": flagged}


def _first_digit(value):
    value = abs(float(value))
    if value <= 0:
        return None
    while value < 1:
        value *= 10
    character = str(value)[0]
    return int(character) if character != "0" else None


def benford_test(amounts):
    digits = [digit for digit in (_first_digit(amount) for amount in amounts.dropna()) if digit]
    sample_size = len(digits)
    if sample_size == 0:
        raise ValueError("Benford analysis requires at least one non-zero amount")
    counts = pd.Series(digits).value_counts().reindex(range(1, 10), fill_value=0)
    observed = counts / sample_size
    expected = pd.Series(BENFORD)
    chi_square = (((counts - sample_size * expected) ** 2) / (sample_size * expected)).sum()
    mad = (observed - expected).abs().mean()
    table = pd.DataFrame(
        {
            "digit": range(1, 10),
            "observed_freq": observed.values.round(4),
            "expected_freq": expected.values.round(4),
            "observed_count": counts.values,
        }
    )
    conformity = (
        "close" if mad < 0.006 else "acceptable" if mad < 0.012 else "marginal" if mad < 0.015 else "nonconformity"
    )
    return {
        "check": "benford",
        "n": sample_size,
        "chi_square": round(float(chi_square), 2),
        "mad": round(float(mad), 5),
        "conformity": conformity,
        "table": table,
    }
