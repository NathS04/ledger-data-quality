-- Ledger Data Quality — Analytical SQL Queries
-- Run against: data/processed/ledger.db (SQLite)

-- 1. Total spend by vendor (top 15)
SELECT
    v.vendor_id,
    v.vendor_name,
    COUNT(t.transaction_id) AS transaction_count,
    ROUND(SUM(t.amount), 2) AS total_spend,
    ROUND(AVG(t.amount), 2) AS avg_amount
FROM transactions t
LEFT JOIN vendors v ON t.vendor_id = v.vendor_id
WHERE t.amount IS NOT NULL
GROUP BY v.vendor_id, v.vendor_name
ORDER BY total_spend DESC
LIMIT 15;


-- 2. Monthly spend trend
SELECT
    SUBSTR(t.transaction_date, 1, 7) AS year_month,
    COUNT(*) AS transaction_count,
    ROUND(SUM(t.amount), 2) AS total_spend
FROM transactions t
WHERE t.transaction_date IS NOT NULL
  AND t.amount IS NOT NULL
GROUP BY SUBSTR(t.transaction_date, 1, 7)
ORDER BY year_month;


-- 3. Spend by GL account
SELECT
    t.account_code,
    COUNT(*) AS transaction_count,
    ROUND(SUM(t.amount), 2) AS total_spend,
    ROUND(SUM(t.amount) * 100.0 / SUM(SUM(t.amount)) OVER (), 2) AS pct_of_total
FROM transactions t
WHERE t.amount IS NOT NULL
GROUP BY t.account_code
ORDER BY total_spend DESC;


-- 4. Orphan transactions (referential integrity failures)
SELECT
    t.transaction_id,
    t.vendor_id,
    t.vendor_name,
    t.amount,
    t.transaction_date
FROM transactions t
LEFT JOIN vendors v ON t.vendor_id = v.vendor_id
WHERE v.vendor_id IS NULL;


-- 5. Duplicate transaction IDs
SELECT
    transaction_id,
    COUNT(*) AS occurrence_count,
    GROUP_CONCAT(source_file, ', ') AS source_files
FROM transactions
GROUP BY transaction_id
HAVING COUNT(*) > 1
ORDER BY occurrence_count DESC;


-- 6. Running total of spend over time (window function)
SELECT
    t.transaction_id,
    t.transaction_date,
    t.vendor_name,
    ROUND(t.amount, 2) AS amount,
    ROUND(
        SUM(t.amount) OVER (
            ORDER BY t.transaction_date, t.transaction_id
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ),
        2
    ) AS running_total
FROM transactions t
WHERE t.amount IS NOT NULL
  AND t.transaction_date IS NOT NULL
ORDER BY t.transaction_date, t.transaction_id
LIMIT 100;


-- 7. Top vendors by exception-prone transactions (orphans + duplicates proxy)
WITH orphan_txns AS (
    SELECT t.vendor_id, t.transaction_id
    FROM transactions t
    LEFT JOIN vendors v ON t.vendor_id = v.vendor_id
    WHERE v.vendor_id IS NULL
),
dup_ids AS (
    SELECT transaction_id
    FROM transactions
    GROUP BY transaction_id
    HAVING COUNT(*) > 1
)
SELECT
    t.vendor_id,
    MAX(t.vendor_name) AS vendor_name,
    COUNT(DISTINCT CASE WHEN o.transaction_id IS NOT NULL THEN t.transaction_id END) AS orphan_count,
    COUNT(DISTINCT CASE WHEN d.transaction_id IS NOT NULL THEN t.transaction_id END) AS dup_id_count
FROM transactions t
LEFT JOIN orphan_txns o ON t.transaction_id = o.transaction_id
LEFT JOIN dup_ids d ON t.transaction_id = d.transaction_id
GROUP BY t.vendor_id
HAVING orphan_count > 0 OR dup_id_count > 0
ORDER BY orphan_count + dup_id_count DESC;
