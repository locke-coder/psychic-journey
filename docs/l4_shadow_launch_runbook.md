# L4-Shadow Launch Runbook

Created: 2026-06-12 KST.

## 1. Purpose

This runbook defines the L4-Shadow Mode launch procedure for the month-end
sales forecasting app.

L4-Shadow allows multiple restricted internal users to validate the app in
parallel with the existing operating flow. It is a shadow validation stage, not
official production operation.

## 2. Launch Conditions

L4-Shadow may start only when all launch conditions below are satisfied or
explicitly accepted as conditions by LOCKE.

| Condition | Required status | R04D status |
| --- | --- | --- |
| Pytest | PASS | PASS, 262 passed |
| Gate Runner ALL | PASS | PASS |
| G23 outputs latest strict | PASS | PASS |
| `outputs/latest` strict check | PASS | PASS |
| Deploy source working tree | Clean | Clean |
| Remote HEAD | Verified | Verified for `origin/main` |
| Safe reconcile commit deployed | Required | `f77e0103071fcc78e79658ab17aaccb84924ebe3` |
| R04B L4-Shadow policy | Approved | Approved by LOCKE |
| Access scope | Invited internal users only | Required |
| Password/auth gate | Maintained | Outer gate confirmed, inner UI manual check pending |

The L4 traceability tool remains a tool-level exception because it verifies the
current deploy branch name against the remote branch of the same name. R04D
uses the independent `origin/main` and `ls-remote refs/heads/main` verification
as the launch deploy basis.

## 3. User Scope

- Only LOCKE-approved internal users may participate.
- Actual invited user emails are managed outside this repository.
- The repository records the group as:
  `LOCKE-approved internal users, managed outside repository`.
- External forwarding is prohibited.
- Access must be removed after the shadow period, role change, or STOP
  decision.

## 4. Data Scope

Only the current aggregate input columns are allowed:

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

Prohibited data must not be entered, uploaded, stored, exported, pasted into
feedback, or included in file names:

- Customer name.
- Phone number.
- Address.
- Contract number.
- Resident registration number.
- Personal identifying information.
- Customer-level transaction ledger.
- Contract-level transaction ledger.
- Raw CRM export.
- Secrets, keys, or passwords.

`memo` may contain only non-identifying operating notes. File names must also
avoid identifiers.

## 5. Execution Flow

1. Access the approved Streamlit URL.
2. Confirm password/auth gate before reaching the app.
3. Upload an input file that uses only the allowed aggregate columns.
4. Review validation messages before interpreting results.
5. Check KPI cards and target status.
6. Review Scenario Grid.
7. Review Report Text.
8. Download Excel output only if needed for the approved internal shadow group.
9. Review History and Backtest views.
10. Submit feedback using the L4-Shadow feedback form.

## 6. Shadow Principles

- App results do not replace official operating judgment, reporting, or closing
  decisions.
- Existing operating and reporting flows continue in parallel.
- Differences between app output and existing judgment must be recorded.
- Feedback is used to determine production gaps, not to approve production by
  itself.
- Excel output is shadow evidence only and must not be circulated externally.

## 7. Stop Conditions

Stop or escalate L4-Shadow if any condition below occurs:

- Customer, contract, personal, secret, key, or password data is entered.
- Password or auth instruction is exposed.
- An unapproved user obtains access.
- App URL, Excel output, or reports are externally shared.
- App result is used as an official production decision.
- Calculation result and Excel output do not match.
- O1/O2/O3 or P1/P2/P3 strategy output is missing.
- Validation errors are unclear enough to cause repeated misuse.
- App bootstrap or runtime errors repeat.

## 8. Evidence Records

Use these R04D evidence files for launch review:

- `audit/logs/r04d_pytest.txt`
- `audit/logs/r04d_gate_runner_all.json`
- `audit/logs/r04d_gate_G23_outputs_latest_strict.json`
- `audit/logs/r04d_outputs_latest_strict.txt`
- `audit/logs/r04d_remote_head_verification.txt`
- `audit/logs/r04d_deploy_traceability_l3.txt`
- `audit/logs/r04d_deploy_traceability_l4.txt`
- `audit/logs/r04d_streamlit_smoke.txt`
- `audit/logs/r04d_audit_package_check.txt`

## 9. Launch Decision Basis

R04D launch decision: `CONDITIONAL_GO`.

Reason: tests, gates, strict output checks, deploy source cleanliness, and
independent remote HEAD verification passed. The deployed app remains gated, so
the inner UI element check is pending manual confirmation by an approved user.

L4-Production remains `NOT_APPROVED`.
