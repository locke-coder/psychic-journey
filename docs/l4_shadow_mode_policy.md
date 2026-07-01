# L4-Shadow Mode Policy

Approval date: 2026-06-11 KST.

## 1. Purpose

This document defines the L4-Shadow Mode operating policy for the month-end
sales forecasting app.

L4-Shadow is the stage where multiple restricted internal users validate the app
in parallel with the existing operating flow by using aggregate real-data-like
inputs. It is not official production operation.

## 2. Stage Definitions

| Stage | Definition | Data scope | Decision authority |
| --- | --- | --- | --- |
| L3 | Sample / anonymous pilot | Sample or anonymous data only | LOCKE |
| L4-Shadow | Restricted internal aggregate real-data shadow validation | LOCKE-approved aggregate inputs only | LOCKE |
| L4-Production | Official production operation | Governed production data only | TBD official production approval |

The L3 sample / anonymous restriction remains valid for L3. R04B adds
L4-Shadow as a separate restricted validation stage; it does not approve
L4-Production.

## 3. L4-Shadow Principles

- App results do not replace official operating judgment, reporting, or closing
  decisions.
- Existing month-end operating and reporting flows continue in parallel.
- Differences between app results and existing judgments are reviewed as
  validation evidence.
- Usability, result interpretation, report text, Excel sharing,
  Backtest, and History operation are validated together.
- Only LOCKE-approved internal invited users may participate.
- Shadow Mode results are used only as evidence for deciding whether the app can
  move toward L4-Production.

## 4. Allowed Input Data

L4-Shadow allows only the current aggregate input columns:

- `date`
- `day_name`
- `business_day_no`
- `is_close_day`
- `close_type`
- `sales_target_daily`
- `recognized_target_daily`
- `sales_actual_cum`
- `recognized_actual_cum`
- `memo`, with no identifiers

Allowed data level:

- Aggregate daily target values.
- Aggregate cumulative performance values.
- Aggregate recognized performance values.
- Daily target and cumulative actual values needed for month-end forecasting.
- Operating aggregates that are not customer-level, contract-level, or
  person-level records.

## 5. Prohibited Data

The following must not be entered, uploaded, stored, exported, pasted into
feedback, or included in file names:

- Customer name.
- Phone number.
- Address.
- Contract number.
- Resident registration number.
- Employee personal information.
- Customer-level transaction data.
- Contract-level transaction data.
- Raw CRM export.
- Secrets.
- Keys.
- Passwords.

Public broad real-data use is prohibited.

## 6. Memo Rules

- `memo` may contain only non-identifying operating reference notes.
- Customer names, contract numbers, phone numbers, addresses, and employee real
  names are prohibited in `memo`.
- File names must not contain identifiers.
- If any identifier is found in `memo`, the input file must be removed from
  shadow circulation immediately and recreated without the identifier.

## 7. Access Control

- Internal invited users only.
- LOCKE approves the invite list.
- The current Streamlit URL may be used only with the password gate maintained.
- Streamlit private or invited-user settings may be added if needed.
- The viewer list must be reviewed before launch.
- Viewer access must be removed after the shadow period or role change.
- External forwarding is prohibited.
- Actual invited-user email addresses are managed in a separate operating note
  and are not recorded in this repository document.

## 8. Output Control

- Excel download is allowed only for invited shadow users.
- Outputs and Excel files must not be shared externally.
- Outputs and Excel files must not be uploaded to public drives.
- Sharing is limited to the approved internal shadow group.
- Output file names must not contain sensitive identifiers.
- App outputs must not be used as official production reports during
  L4-Shadow.

## 9. Final Actual Shadow Policy

- Aggregate monthly final actuals are allowed during shadow validation.
- LOCKE is the final_actual shadow owner.
- Customer-level, contract-level, or person-level final_actual data is
  prohibited.
- Before L4-Production, final_actual governance must be redefined, including
  official owner, cutoff date, correction authority, deletion authority,
  retention period, and audit log standard.

## 10. Approval Roles

| Role | Owner |
| --- | --- |
| L4-Shadow owner | LOCKE |
| Invited users approver | LOCKE |
| Password owner | LOCKE |
| Feedback owner | LOCKE |
| final_actual shadow owner | LOCKE |
| L4-Production approver | TBD, official company operation approval required |

## 11. Stop Conditions

L4-Shadow must stop or escalate if any of the following occurs:

- Accidental customer data entry.
- Password exposure.
- Unapproved viewer access.
- Output shared outside the approved group.
- `memo` contains identifiers.
- App becomes public without approval.
- App result is used as an official production decision without approval.
- Calculation mismatch between the app and Excel.
- O1/O2/O3 or P1/P2/P3 strategy output is missing.
- Excel download failure persists.

## 12. Shadow Success Criteria

L4-Shadow may be considered successful only when:

- Multiple approved users complete input, KPI, scenario, report, and Excel flow.
- UNDER / ON / OVER interpretation is consistent.
- Excel output is usable.
- No sensitive-data incident occurs.
- No calculation mismatch is found.
- Feedback is collected.
- A production gap list is created.

