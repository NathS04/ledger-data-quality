import numpy as np
import pandas as pd

from src import anomaly
from src import quality_checks as qc


def _df(records):
    return pd.DataFrame(records)


def test_completeness_flags_missing():
    frame = _df(
        [
            {"transaction_id": "T1", "vendor_id": "V1", "txn_date": pd.Timestamp("2024-01-01"), "amount": 10.0},
            {"transaction_id": "T2", "vendor_id": None, "txn_date": pd.Timestamp("2024-01-02"), "amount": 20.0},
        ]
    )
    result = qc.check_completeness(frame)
    assert not result["passed"] and result["n_flagged"] == 1


def test_uniqueness_flags_dupe_ids():
    frame = _df(
        [
            {"transaction_id": "T1", "vendor_id": "V1", "txn_date": pd.Timestamp("2024-01-01"), "amount": 10.0},
            {"transaction_id": "T1", "vendor_id": "V1", "txn_date": pd.Timestamp("2024-01-03"), "amount": 11.0},
        ]
    )
    assert qc.check_uniqueness(frame)["n_flagged"] == 2


def test_referential_integrity():
    transactions = _df(
        [
            {"transaction_id": "T1", "vendor_id": "V1", "txn_date": pd.Timestamp("2024-01-01"), "amount": 10.0},
            {"transaction_id": "T2", "vendor_id": "V9", "txn_date": pd.Timestamp("2024-01-01"), "amount": 10.0},
        ]
    )
    vendors = _df([{"vendor_id": "V1", "vendor_name": "Acme"}])
    assert qc.check_referential_integrity(transactions, vendors)["n_flagged"] == 1


def test_reconciliation_detects_variance():
    transactions = _df([{"gl_account": "6000", "amount": 100.0}, {"gl_account": "6000", "amount": 50.0}])
    control = _df([{"gl_account": "6000", "control_total": 200.0}])
    result = qc.check_reconciliation(transactions, control)
    assert not result["passed"] and result["n_breaks"] == 1


def test_benford_runs():
    result = anomaly.benford_test(pd.Series(np.random.lognormal(6, 1.1, 2000)))
    assert set(result["table"]["digit"]) == set(range(1, 10))
