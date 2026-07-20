"""Tests for data-quality checks using known-bad data."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from anomaly import benfords_law_test, detect_duplicate_payments  # noqa: E402
from quality_checks import (  # noqa: E402
    check_completeness,
    check_referential_integrity,
    check_reconciliation,
    check_uniqueness,
)


@pytest.fixture
def sample_vendors() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"vendor_id": "V001", "vendor_name": "acme supplies ltd", "country": "UK"},
            {"vendor_id": "V002", "vendor_name": "global tech solutions", "country": "UK"},
        ]
    )


@pytest.fixture
def clean_transactions() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "transaction_id": "TXN-001",
                "vendor_id": "V001",
                "vendor_name": "acme supplies ltd",
                "transaction_date": "2024-06-15",
                "amount": 1500.00,
            },
            {
                "transaction_id": "TXN-002",
                "vendor_id": "V002",
                "vendor_name": "global tech solutions",
                "transaction_date": "2024-06-20",
                "amount": 2300.50,
            },
        ]
    )


def test_completeness_flags_missing_fields(clean_transactions):
    df = clean_transactions.copy()
    df.loc[0, "amount"] = None
    result = check_completeness(df, threshold=0.99)
    assert not result["passed"]
    assert len(result["flagged_rows"]) >= 1
    assert "completeness" in result["flagged_rows"]["_issue_type"].values


def test_uniqueness_catches_duplicate_ids(clean_transactions):
    df = pd.concat([clean_transactions, clean_transactions.iloc[[0]]], ignore_index=True)
    result = check_uniqueness(df)
    assert not result["passed"]
    assert result["flagged_rows"]["transaction_id"].nunique() >= 1


def test_referential_integrity_catches_orphans(clean_transactions, sample_vendors):
    df = clean_transactions.copy()
    df.loc[0, "vendor_id"] = "V999"
    result = check_referential_integrity(df, sample_vendors)
    assert not result["passed"]
    assert len(result["flagged_rows"]) == 1


def test_reconciliation_flags_variance(tmp_path, clean_transactions):
    df = clean_transactions.copy()
    control = pd.DataFrame(
        [
            {"period": "2024-06", "control_amount": 999999.00},
        ]
    )
    control_path = tmp_path / "period_control_totals.csv"
    control.to_csv(control_path, index=False)

    result = check_reconciliation(df, tolerance=0.01, control_path=control_path)
    assert not result["passed"]
    assert len(result["flagged_rows"]) >= 1


def test_duplicate_payment_detection():
    df = pd.DataFrame(
        [
            {
                "transaction_id": "TXN-A",
                "vendor_id": "V001",
                "amount": 500.00,
                "transaction_date": "2024-03-01",
            },
            {
                "transaction_id": "TXN-B",
                "vendor_id": "V001",
                "amount": 500.00,
                "transaction_date": "2024-03-03",
            },
        ]
    )
    result = detect_duplicate_payments(df, window_days=3)
    assert not result["passed"]
    assert len(result["flagged_rows"]) == 2


def test_benford_detects_skewed_distribution(tmp_path):
    # Amounts heavily weighted to leading digit 9 — should fail Benford
    amounts = [9000 + i * 10 for i in range(200)]
    df = pd.DataFrame(
        {
            "transaction_id": [f"TXN-{i}" for i in range(len(amounts))],
            "amount": amounts,
        }
    )
    output = tmp_path / "benford.csv"
    result = benfords_law_test(df, alpha=0.05, output_path=output)
    assert not result["passed"]
    assert output.exists()
    assert result["p_value"] < 0.05
