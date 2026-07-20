# Power BI Dashboard — Build Guide

Build this dashboard in **Power BI Desktop** (~30 minutes). Save the finished file as `outputs/dashboard.pbix`.

---

## Prerequisites

1. Run the pipeline first so outputs exist:

   ```bash
   python src/run_pipeline.py
   ```

2. Install [Power BI Desktop](https://powerbi.microsoft.com/desktop/) (free).

---

## Step 1 — Connect to data

**Option A — CSV files (recommended for portability)**

1. Open Power BI Desktop → **Get data** → **Text/CSV**
2. Import these three files:
   - `outputs/kpis.csv`
   - `outputs/exceptions_report.csv`
   - `outputs/benford.csv`

**Option B — SQLite database (live queries)**

1. **Get data** → search for **SQLite** (install the connector if prompted)
2. Browse to `data/processed/ledger.db`
3. Load tables: `transactions`, `vendors`

---

## Step 2 — Data model (if using SQLite)

Create relationships:

| From | To | Cardinality |
|------|----|-------------|
| `transactions.vendor_id` | `vendors.vendor_id` | Many-to-one |

For CSV-only mode, no relationships are needed — each file is self-contained.

---

## Step 3 — DAX measures (optional, for SQLite mode)

```dax
Total Spend = SUM(transactions[amount])
Transaction Count = COUNTROWS(transactions)
Exception Count = COUNTROWS(exceptions_report)
Duplicate Candidates = CALCULATE(COUNTROWS(exceptions_report), exceptions_report[_issue_type] = "duplicate_payment")
```

If using `kpis.csv`, use the pre-calculated values instead.

---

## Step 4 — Build visuals

### Page 1: Executive Summary

| Visual | Field mapping | Notes |
|--------|---------------|-------|
| **Card — Total Spend** | `kpis[value]` where `metric = total_spend` | Format as currency (£) |
| **Card — Transaction Count** | `kpis[value]` where `metric = transaction_count` | Whole number |
| **Card — Exception Count** | `kpis[value]` where `metric = exception_count` | Whole number |
| **Card — Duplicate Payment Candidates** | `kpis[value]` where `metric = duplicate_payment_candidates` | Whole number |
| **Bar chart — Spend by Vendor** | Axis: `vendor_name`, Value: `SUM(amount)` | Top 10, sorted descending |
| **Line chart — Spend Over Time** | Axis: month from `transaction_date`, Value: `SUM(amount)` | Continuous axis |

### Page 2: Data Quality & Exceptions

| Visual | Field mapping | Notes |
|--------|---------------|-------|
| **Donut chart — Exceptions by Type** | Legend: `_issue_type`, Value: count of rows | From `exceptions_report.csv` |
| **Bar chart — Exceptions by Check** | Axis: `check_name`, Value: count | Shows which checks found the most issues |
| **Table — Exception Detail** | Columns: `transaction_id`, `vendor_name`, `amount`, `_issue_type`, `_issue_reason` | Enable conditional formatting on `_issue_type` |

### Page 3: Benford Analysis

| Visual | Field mapping | Notes |
|--------|---------------|-------|
| **Clustered column — Benford Actual vs Expected** | Axis: `digit`, Values: `actual_pct` and `expected_pct` | From `benford.csv` |
| **Card — Chi-square p-value** | `kpis[value]` where `metric = benford_p_value` | Highlight red if < 0.05 |
| **Card — Checks Passed / Failed** | `checks_passed` / `checks_failed` from KPIs | |

---

## Step 5 — Formatting tips

- **Theme:** Use a clean corporate theme (grey/blue palette works well for finance).
- **Title:** "Ledger Data Quality Dashboard — Synthetic AP/GL Data"
- **Subtitle:** Include the pipeline run date.
- **Conditional formatting:** Red for failed checks, amber for warnings, green for pass.
- **Slicer:** Add a `_issue_type` slicer on the exceptions page for interactive filtering.

---

## Step 6 — Save

Save as:

```
outputs/dashboard.pbix
```

Add a screenshot to the repo (e.g. `docs/dashboard_screenshot.png`) and reference it in the README.

---

## Refresh workflow

Each time you re-run the pipeline:

```bash
python src/run_pipeline.py
```

In Power BI Desktop: **Home → Refresh** to pull updated CSV/SQLite data.

---

## Checklist before adding to CV

- [ ] Pipeline runs end-to-end without errors
- [ ] All three output CSVs populated
- [ ] Dashboard built with all visuals above
- [ ] `dashboard.pbix` saved to `outputs/`
- [ ] GitHub repo set to **Public**
- [ ] Screenshot added to README (optional but recommended)
