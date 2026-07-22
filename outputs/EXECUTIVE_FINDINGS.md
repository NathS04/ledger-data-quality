# Executive Audit Findings

## Purpose and scope

This concise report summarises the deterministic results produced by the ledger data-quality pipeline. It is an independent, synthetic portfolio exercise designed to demonstrate audit analytics techniques; it does not describe a real Deloitte engagement or a real organisation's financial records.

## Findings at a glance

| Audit analytics area | Result | Audit relevance |
|---|---:|---|
| Critical-field completeness | 130 transactions have a missing critical field: 60 amounts, 30 transaction dates, and 40 vendor IDs. | Incomplete fields can impair period allocation, supplier testing, payment analysis, and the reliability of downstream reporting. |
| Vendor-master integrity | 79 transactions reference a populated vendor ID that is absent from the vendor master. | Orphan references indicate potential master-data, interface, or approval-control weaknesses. |
| Financial-data reconciliation | All 6 GL accounts have a variance against their independent control total. | The ledger population does not tie to the control totals and needs investigation before it is relied upon for audit testing. |
| Duplicate-payment screening | 290 transactions share the same vendor, invoice number, and amount as another transaction. | These are potential duplicate payments or repeat postings requiring corroborative evidence. |
| Benford first-digit screening | Digit 9 occurs in 5.39% of populated amounts (544 items), compared with a 4.58% Benford expectation. | The excess identifies a focused population for follow-up, alongside the full population and business context. |

The overall Benford mean absolute deviation is 0.00271, classified by this pipeline as **close**. The elevated digit-9 frequency should be treated as a targeted screening observation rather than a conclusion about the whole ledger.

## Recommended audit follow-up

1. **Establish data reliability.** Obtain the source-system extract criteria, field mapping, and data lineage; reconcile record counts and investigate the missing vendor, date, and amount fields with management.
2. **Test master-data controls.** Inspect the vendor onboarding and change-management controls for the 79 orphan references, including interface-error reports and evidence of timely remediation.
3. **Resolve ledger-to-control variances.** Agree each GL-account variance to a reconciling item, determine whether it is a timing, mapping, completeness, or posting issue, and assess the effect on the audit population.
4. **Investigate duplicate-payment candidates.** Select risk-based samples from the 290 candidates and inspect invoices, purchase orders, goods-received evidence, payment runs, credit notes, and duplicate-payment recovery activity.
5. **Use the digit-9 population for targeted testing.** Consider substantive testing of unusual amounts, manual journals, round-number patterns, approvers, and posting periods, while assessing whether the underlying population is suitable for Benford analysis.
6. **Escalate and communicate.** Summarise validated exceptions, control owners, remediation dates, and residual risk for finance leadership and those charged with governance.

## Interpretation boundary

**Benford analysis is a screening method, not proof of fraud, error, or misconduct.** Any exception must be evaluated with transaction-level evidence, the business process, and the relevant control environment before drawing an audit conclusion.
