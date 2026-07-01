# Final Actual Shadow Procedure

Approval date: 2026-06-11 KST.

## 1. Purpose

This procedure defines how aggregate monthly final_actual values may be used
during L4-Shadow to validate Backtest and History behavior in parallel with the
existing operating flow.

This procedure does not approve official production final_actual governance.

## 2. Allowed

- Aggregate monthly final_actual values.
- Aggregate sales final actual values.
- Aggregate recognized final actual values.
- LOCKE-owned input, correction, and deletion during the shadow period.

## 3. Prohibited

- Customer-level final actuals.
- Contract-level final actuals.
- Person-identifying final actuals.
- Raw transaction uploads.
- Raw CRM export uploads.
- Any final_actual value in a public broad real-data context.

## 4. Procedure

1. LOCKE confirms the aggregate final_actual value before entry.
2. Record a source note for the value, with no identifiers.
3. Enter or update only the aggregate monthly value.
4. Review Backtest behavior after entry.
5. If an error is found, record the correction reason before updating.
6. At the end of the shadow period, review final_actual usability and remaining
   production gaps.

## 5. Correction And Deletion Rules

- If an entry error is found, LOCKE must approve the correction.
- The correction reason must be recorded.
- If deletion is required, the deletion reason must be recorded.
- During L4-Shadow, the stored value is validation evidence only and is not the
  official ledger of record.

## 6. Required Before L4-Production

Before L4-Production, the following must be redefined and approved:

- Official final_actual owner.
- Cutoff date.
- Correction authority.
- Deletion authority.
- Retention period.
- Audit log standard.
- Production rollback criteria.

