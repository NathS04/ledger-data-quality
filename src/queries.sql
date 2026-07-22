-- 1. Spend by vendor (top 20)
SELECT v.vendor_name, ROUND(SUM(t.amount), 2) AS total_spend, COUNT(*) AS n_txns
FROM transactions t JOIN vendors v ON t.vendor_id = v.vendor_id
WHERE t.amount IS NOT NULL
GROUP BY v.vendor_name ORDER BY total_spend DESC LIMIT 20;

-- 2. Monthly spend trend
SELECT strftime('%Y-%m', t.txn_date) AS month, ROUND(SUM(t.amount), 2) AS total_spend
FROM transactions t
WHERE t.txn_date IS NOT NULL AND t.amount IS NOT NULL
GROUP BY month ORDER BY month;

-- 3. Spend by GL account with running total (window function)
SELECT gl_account, ROUND(SUM(amount), 2) AS account_total,
       ROUND(SUM(SUM(amount)) OVER (ORDER BY gl_account), 2) AS running_total
FROM transactions WHERE amount IS NOT NULL
GROUP BY gl_account ORDER BY gl_account;

-- 4. Potential duplicate payments (same vendor + invoice + amount)
SELECT vendor_id, invoice_number, amount, COUNT(*) AS occurrences
FROM transactions WHERE amount IS NOT NULL
GROUP BY vendor_id, invoice_number, amount
HAVING COUNT(*) > 1 ORDER BY occurrences DESC LIMIT 10;

-- 5. Orphan transactions (vendor_id absent from vendors master)
SELECT t.transaction_id, t.vendor_id, t.amount
FROM transactions t LEFT JOIN vendors v ON t.vendor_id = v.vendor_id
WHERE v.vendor_id IS NULL AND t.vendor_id IS NOT NULL LIMIT 10;
