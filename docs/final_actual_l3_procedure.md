# R03 L3 Temporary Final Actual Procedure

This procedure defines the temporary L3 handling of completed-month actuals for
Backtest review. It does not approve real sales actuals for L3. R04B separately
defines L4-Shadow aggregate monthly final_actual handling under LOCKE ownership.

## 1. Purpose

The purpose is to store completed-month actual values so Backtest quality can be
checked during the L3 internal pilot.

R03.1A LOCKE values:

| Field | Value |
| --- | --- |
| Pilot users | LOCKE only. Optional internal reviewer: maximum 1, name recorded only after separate approval. |
| Pilot period | 2026-06-11 to 2026-06-17 KST |
| Access method | Current Streamlit URL + password gate. Sample / anonymous data only. Public Streamlit real-data use prohibited. |
| Password owner | LOCKE |
| Sample dataset | 1 `UNDER_TARGET` sample, 1 `ON_TARGET` sample, 1 `OVER_TARGET` sample. No real customer names, contract numbers, phone numbers, addresses, or real sales data. |
| Feedback owner | LOCKE |
| Go/no-go owner | LOCKE |
| Data scope | sample / anonymous only |
| Real data allowed | no for L3; aggregate monthly final_actual allowed only in L4-Shadow under LOCKE ownership |
| Public Streamlit real-data use allowed | no |

Because all required launch values are recorded, this procedure may be used
during the controlled L3 pilot for sample or anonymous review only. It does not
approve real `final_actual` operation for L3, customer/contract/person-level
final_actual data, or L4-Production use.

## R04B Stage Update

Operating stages are now defined as:

- L3: sample / anonymous pilot.
- L4-Shadow: restricted internal aggregate real-data shadow validation.
- L4-Production: official production operation.

This document remains the L3 procedure. L4-Shadow final_actual handling is
defined in `docs/final_actual_shadow_procedure.md` and allows only aggregate
monthly final_actual values under LOCKE ownership. L4-Production final_actual
governance remains not approved.

R04A deploy source clean local commit:
`5be44e16b31da425d0e6fab326781a01581af25e`.

The L3 procedure is limited to verifying workflow behavior:

- Saving or loading a completed-month actual value.
- Matching forecast history to completed-month actuals.
- Reviewing Backtest output.
- Capturing feedback on whether the flow is understandable.

## 2. L3 Limits

Allowed:

- Sample completed-month data.
- Anonymous completed-month data.
- Aggregate test values with no customer, contract, personal, or account
  identifiers.

Not allowed:

- Real sales performance values.
- Real recognized revenue values.
- Names of customers, employees, partners, or accounts.
- Customer addresses, phone numbers, contract numbers, or personal identifiers.
- Public URL entry of real completed-month actuals.
- Team sharing of real-data files through this L3 procedure.

## 3. Input Fields

The temporary L3 procedure may use only these fields:

| Field | Rule |
| --- | --- |
| `month` | Month under review, using a non-sensitive sample or anonymous month. |
| `metric_type` | `sales` or `recognized`, or the app-supported metric label. |
| `final_actual_sales` | Sample or anonymous completed-month sales amount only. |
| `final_actual_recognized` | Sample or anonymous completed-month recognized amount only. |
| `memo` | Optional. Must not include sensitive information. |

If a memo is needed, use generic notes such as `sample close complete` or
`anonymous backtest case`. Do not include customer or contract context.

## 4. Procedure

1. Create or select a sample completed-month case.
2. Confirm the case contains no real sales data or sensitive identifiers.
3. Use the app-supported final actual file or storage module.
4. Save only the fields allowed in this procedure.
5. Open the Backtest tab.
6. Confirm forecast history matches to the completed-month actual by month and
   metric.
7. Capture the Backtest result screen.
8. Record feedback in `docs/pilot_feedback_form.md`.
9. Record any issue in `audit/pilot_checklist.md`.

Do not hand-edit real operational records during L3.

## 5. Prohibited Before Applicable Approval

The following remain prohibited in L3:

- Saving real actual sales results.
- Saving real recognized revenue results.
- Uploading team shared files containing real completed-month actuals.
- Entering real completed-month actuals through a Public URL.
- Using final actual values for official business decisions.
- Expanding access beyond approved internal users.

In L4-Shadow, only aggregate monthly final_actual values are allowed, and LOCKE
is the input, correction, and deletion owner. Customer-level, contract-level,
and person-level final_actual data remain prohibited.

## 6. Requirements Before L4-Production

Before L4-Production, the official production approver must approve and
document:

- Official `final_actual` owner.
- Cutoff date.
- Correction authority.
- Deletion authority.
- Retention period.
- Audit log standard.
- Production real-data policy.
- Production access control.
- Password and secret rotation.
- Production rollback criteria.

Until those items are approved, L4-Production `final_actual` use remains not
approved.
