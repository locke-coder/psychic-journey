# Real Data Shadow Approval Matrix

Approval date: 2026-06-11 KST.

## 1. Purpose

This matrix defines approval boundaries for using aggregate real-data-like
inputs during L4-Shadow.

L4-Shadow is restricted internal aggregate validation. It is not public broad
real-data use and it is not L4-Production.

## 2. Approved Scope

Allowed in L4-Shadow:

- Aggregate daily targets.
- Aggregate cumulative actuals.
- Aggregate recognized actuals.
- Aggregate monthly final_actual values.

Excluded from L4-Shadow:

- Customer-level data.
- Contract-level data.
- Person-level data.
- Raw transaction ledgers.
- Raw CRM exports.
- Secrets, keys, and passwords.

## 3. Approval Matrix

| Domain | Allowed in L4-Shadow | Approver | Operator | Reviewer | Notes |
| --- | --- | --- | --- | --- | --- |
| Input daily target | Yes | LOCKE | Invited user | LOCKE | Aggregate daily target only. |
| Input cumulative actual | Yes | LOCKE | Invited user | LOCKE | Aggregate cumulative performance only. |
| Recognized cumulative actual | Yes | LOCKE | Invited user | LOCKE | Aggregate recognized performance only. |
| Memo | Conditional | LOCKE | Invited user | LOCKE | No identifiers; operating notes only. |
| Excel download | Yes | LOCKE | Invited user | LOCKE | No external sharing or public upload. |
| final_actual aggregate value | Yes | LOCKE | LOCKE | LOCKE | Aggregate monthly value only. |
| Invited user list | Yes | LOCKE | LOCKE | LOCKE | Actual emails managed separately. |
| Password ownership | Yes | LOCKE | LOCKE | LOCKE | Password gate maintained. |
| Feedback collection | Yes | LOCKE | Invited user | LOCKE | Feedback must not include identifiers. |
| Production conversion | No for shadow | TBD official approval | TBD | TBD | Requires separate L4-Production approval. |

## 4. Escalation Conditions

Escalate to LOCKE and pause the affected activity if any of the following
occurs:

- Input columns change.
- Customer-level, contract-level, or person-level data is requested or added.
- External sharing is requested.
- App output is proposed as a replacement for official reporting.
- final_actual is proposed for official production operation.
- Invited-user scope expands.
- Password exposure occurs.
- Identifiers are found in `memo`, file names, feedback, screenshots, or
  outputs.

