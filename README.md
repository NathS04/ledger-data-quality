# Ledger Data Quality & Reconciliation Pipeline

A reproducible Python pipeline that ingests messy accounts-payable / general-ledger exports, cleans and standardises them, loads them into SQLite, runs automated data-quality checks and anomaly detection, and produces dashboard-ready outputs for Power BI.

Built as a portfolio project demonstrating end-to-end data-analyst skills: ingestion, cleansing, SQL, reconciliation, statistical anomaly detection, and BI reporting.

> **Note:** The dataset is **synthetic** with deliberately injected data-quality issues. This keeps the project fully reproducible without relying on confidential or hard-to-find real exports.

---

## What it does

| Stage | Description |
|-------|-------------|
| **Generate** | Synthesises ~10,000 AP/GL transactions with realistic mess (bad dates, currency formats, duplicates, orphan vendor IDs, Benford skew) |
| **Ingest** | Reads all CSV/XLSX files from `data/raw/` and concatenates them |
| **Clean** | Standardises dates, amounts, vendor names; removes exact duplicates |
| **Load** | Loads cleaned data into SQLite (`transactions`, `vendors` tables) |
| **Quality checks** | Completeness, uniqueness, referential integrity, period reconciliation |
| **Anomaly detection** | Duplicate-payment candidates + Benford's Law chi-square test |
| **Outputs** | Exception report, KPIs, and Benford breakdown for Power BI |

---

## Architecture

```
data/raw/  ──►  ingest.py  ──►  clean.py  ──►  load_db.py  ──►  ledger.db
                                      │                              │
                                      ▼                              ▼
                              processed CSVs              quality_checks.py
                                                                    │
                                                                    ▼
                                                            anomaly.py
                                                                    │
                                                                    ▼
                                              outputs/exceptions_report.csv
                                              outputs/kpis.csv
                                              outputs/benford.csv
                                                                    │
                                                                    ▼
                                              Power BI Desktop (manual step)
```

---

## Quick start

**Requirements:** Python 3.11+

```bash
# 1. Clone and install dependencies
git clone https://github.com/NathS04/ledger-data-quality.git
cd ledger-data-quality
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. (Optional) Generate synthetic raw data — skipped automatically if data/raw/ is empty
python src/generate_data.py

# 3. Run the full pipeline
python src/run_pipeline.py

# 4. Run tests
pytest tests/ -v
```

The pipeline auto-generates raw data on first run if `data/raw/` is empty.

---

## Data-quality checks (plain English)

### Completeness
Measures the percentage of non-null values in critical columns (`transaction_id`, `vendor_id`, `vendor_name`, `transaction_date`, `amount`). Rows with missing critical fields are flagged. The check fails if any column falls below 95% completeness.

### Uniqueness
Detects duplicate `transaction_id` values — each transaction should appear exactly once. Duplicate IDs indicate export errors or double-loading.

### Referential integrity
Every transaction's `vendor_id` must exist in the `vendors` master table. Orphan references are flagged (often caused by stale exports or manual entry errors).

### Reconciliation
Sums transaction amounts by calendar month and compares them to pre-calculated control totals. Any period with variance above £0.01 is flagged — this confirms the loaded data ties back to expected book totals.

### Duplicate-payment detection
Groups transactions by vendor and amount, then flags pairs occurring within a 3-day window — a common indicator of accidental double payments.

### Benford's Law
Compares the leading-digit distribution of transaction amounts against Benford's expected frequencies using a chi-square test. Significant deviation (p < 0.05) suggests potential fraud, manual manipulation, or data-entry bias.

---

## Example findings

After running the pipeline on the synthetic dataset, expect results similar to:

| Check | Typical result |
|-------|----------------|
| Completeness | FAIL — ~2% of rows missing critical fields |
| Uniqueness | FAIL — duplicate transaction IDs present |
| Referential integrity | FAIL — orphan vendor IDs injected |
| Reconciliation | FAIL — injected duplicates/amount changes cause period variances |
| Duplicate payments | FAIL — ~80+ candidate rows flagged |
| Benford's Law | FAIL — inflated 8/9 leading digits deviate from expected |

See `outputs/exceptions_report.csv` for every flagged row with issue type and reason.

---

## SQL queries

Analytical queries live in `src/queries.sql`. Run them against the SQLite database:

```bash
sqlite3 data/processed/ledger.db < src/queries.sql
```

Queries include spend by vendor, monthly trends, GL account breakdown, orphan detection, duplicate IDs, and running totals (window function).

---

## Power BI dashboard

The `.pbix` file must be built manually in **Power BI Desktop** (see `outputs/DASHBOARD.md` for step-by-step instructions). Connect to:

- `outputs/kpis.csv`
- `outputs/exceptions_report.csv`
- `outputs/benford.csv`

Or connect directly to `data/processed/ledger.db` via the SQLite connector.

<!-- Uncomment after building the dashboard:
![Dashboard screenshot](docs/dashboard_screenshot.png)
-->

---

## Project structure

```
ledger-data-quality/
├── README.md
├── requirements.txt
├── data/
│   ├── raw/                 # Messy input exports (generated)
│   └── processed/           # Cleaned CSVs + SQLite DB
├── src/
│   ├── generate_data.py     # Synthetic data with injected issues
│   ├── ingest.py
│   ├── clean.py
│   ├── load_db.py
│   ├── quality_checks.py
│   ├── anomaly.py
│   ├── queries.sql
│   └── run_pipeline.py
├── outputs/
│   ├── exceptions_report.csv
│   ├── kpis.csv
│   ├── benford.csv
│   └── DASHBOARD.md
└── tests/
    └── test_quality_checks.py
```

---

## Limitations

- **Synthetic data only** — patterns are realistic but not real financial records.
- **SQLite** — portable for demos; production would use PostgreSQL/SQL Server with proper indexing and access controls.
- **Reconciliation tolerance** — fixed at £0.01; real implementations need configurable thresholds and FX handling.
- **Benford's Law** — most effective on large, naturally occurring datasets; small samples or constrained amount ranges can produce false positives.
- **Power BI** — dashboard assembly requires Power BI Desktop (Windows/macOS); the `.pbix` is not generated by this repo.
- **UK public spend data** — not included by default, but the ingest layer accepts any CSV/XLSX dropped into `data/raw/` with compatible columns.

---

## Tech stack

Python 3.11+ · pandas · SQLAlchemy · SQLite · openpyxl · scipy · numpy · matplotlib · pytest · Power BI Desktop

---

## License

MIT — free to use and adapt for portfolio and learning purposes.
