# Power BI dashboard guide

The pipeline writes four dashboard-ready CSV files into `outputs/`:

- `kpis.csv` — one-row summary for KPI cards.
- `exceptions_report.csv` — transaction-level exceptions with `__check` and `__issue` categories.
- `benford.csv` — observed and expected first-digit frequencies.
- `reconciliation.csv` — control totals, actual totals, variances, and tie-out status by GL account.

## Manual completion status

This repository does not include a `dashboard.pbix` file or a dashboard screenshot. Build the report locally in Power BI Desktop from the CSV files above; the steps below describe the required manual work.

## Build the report

1. Run `python -m src.run_pipeline` from the repository root.
2. In Power BI Desktop, choose **Get data → Text/CSV** and import all four CSVs above.
3. Set amount, total, variance, and frequency fields to decimal numbers; set counts to whole numbers.
4. Build the visuals below. If you choose to retain the report locally, save it as `outputs/dashboard.pbix`.

## Recommended page layout

### Executive overview

- KPI cards: `total_spend`, `total_transactions`, `missing_field_rows`, `duplicate_payment_candidates`, and `reconciliation_breaks` from `kpis.csv`.
- Bar chart: exception count by `__check` from `exceptions_report.csv`.
- Table: GL account, control total, actual total, variance, and reconciled from `reconciliation.csv`.

### Exception analysis

- Donut or bar chart: exception rows grouped by `__issue`.
- Detail table: transaction ID, vendor ID, invoice number, date, amount, source file, check, and issue.
- Add slicers for `__check`, `__issue`, GL account, and source file.

### Benford analysis

- Clustered column chart with `digit` on the axis and both `observed_freq` and `expected_freq` as values.
- Cards for `benford_mad` and `benford_conformity` from `kpis.csv`.

Benford analysis is a screening heuristic. An unusual digit distribution is not evidence of fraud and should be followed by transaction-level investigation.
