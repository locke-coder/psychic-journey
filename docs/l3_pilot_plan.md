# R03 L3 Internal Pilot Plan

This document defines the limited L3 internal pilot plan for the input-driven
month-end sales forecasting tool.

## R03.1A LOCKE Launch Values

The following values are fixed from the R03.1A `LOCKE_DECISION_BLOCK`.

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
| Real data allowed | no for L3; restricted aggregate real-data allowed only in L4-Shadow under LOCKE approval |
| Public Streamlit real-data use allowed | no |

All required launch values are now recorded. The launch approval final decision
is `CONDITIONAL_GO` because the controlled L3 pilot may run only under
sample/anonymous data restrictions and recorded known warnings. L4-Production,
public broad real-data use, and official real-data operation remain prohibited.
R04B separately defines L4-Shadow as restricted internal aggregate real-data
shadow validation under LOCKE approval.

## R04B Stage Update

R04B reframes the operating path into three stages:

- L3: sample / anonymous pilot.
- L4-Shadow: restricted internal aggregate real-data shadow validation.
- L4-Production: official production operation.

The L3 pilot described in this document remains sample / anonymous only.
L4-Shadow may use only LOCKE-approved aggregate inputs through the current input
columns, with invited internal users, password gate, no external sharing, no
identifiers in `memo` or file names, and no replacement of official reporting.

R04A deploy source clean local commit:
`5be44e16b31da425d0e6fab326781a01581af25e`.

## 1. Pilot Purpose

The L3 pilot validates whether the current release is fit for controlled
business-facing internal use without changing formulas, calculation modules, or
test expectations.

The pilot must confirm:

- Business users can follow the flow from input, validation, forecast, scenario
  review, report text, and Excel download.
- Users understand the practical meaning of O1/O2/O3 over-target strategies and
  P1/P2/P3 under-target response strategies.
- KPI values, `target_status`, `target_variance`, `surplus_to_target`, and the
  next-close cumulative-line required amount can be interpreted correctly.
- Backtest and forecast history provide useful operating evidence.
- The pilot can run with sample or anonymous data only, with no sensitive
  information exposed.

## 2. Pilot Scope

Scope: L3 Internal Pilot.

Allowed data scope:

- `sample` data.
- `anonymous` data.
- Aggregated operating amounts with no customer, contract, personal, or account
  identifiers.

Not allowed:

- Real sales data in L3.
- Customer names, phone numbers, addresses, contract numbers, resident
  registration numbers, or any other sensitive identifiers.
- Real business data in a public broad Streamlit deployment.
- Any implication that Public Streamlit is approved for broad real-data use.
- Formula changes to F1/F2/F3, P1/P2/P3, or O1/O2/O3.
- Changes to `app.py`, `src`, tests, config, deploy source, or existing output
  artifacts during R03.

The pilot is limited to approved internal users only.

## 3. Pilot Participants

Pilot access is limited to LOCKE by default. LOCKE may add no more than one
internal reviewer, and the reviewer name must be recorded only after separate
approval.

| Role | Participant | Responsibility |
| --- | --- | --- |
| Owner | LOCKE | Owns pilot go/no-go, scope control, issue triage, and evidence review. |
| Operator | LOCKE | Runs the app with sample or anonymous input and records daily results. |
| Reviewer | Optional approved internal reviewer, maximum 1 | Reviews KPI, scenario, report, Excel, Backtest, and feedback quality only after separate approval. |
| Observer | None by default | May be the optional approved reviewer only if separately approved. |
| Password owner | LOCKE | Owns pilot password handling and rotation confirmation before access opens. |
| Feedback owner | LOCKE | Collects and summarizes pilot feedback without sensitive information. |

Access must not be expanded without an explicit pilot approval note.

## 4. Pilot Period

Pilot period: 2026-06-11 to 2026-06-17 KST.

Fixed duration: 7 calendar days.

Minimum case coverage:

- All 3 approved sample input cases must be exercised.
- Coverage must include 1 `UNDER_TARGET` sample, 1 `ON_TARGET` sample, and 1
  `OVER_TARGET` sample.

The pilot period must be short enough to remain controlled, but long enough to
capture validation behavior, report interpretation, Excel export, forecast
history, and Backtest review.

## 5. Success Criteria

The pilot may be considered successful at L3 only when all of the following are
true:

- The input file can be prepared by the operator using sample or anonymous data.
- Validation errors, if raised, can be understood and corrected by the operator.
- KPI values, scenario output, and report text can be interpreted without
  calculation ambiguity.
- `target_status` is understood as under-target, on/near-target, or
  over-target.
- P1/P2/P3 and O1/O2/O3 strategy meanings are understood in operating terms.
- The Excel report can be downloaded, opened, and shared only inside the
  approved pilot group.
- Forecast history or Backtest flow is understood.
- No sensitive information is entered, displayed, saved, exported, or included
  in feedback.

## 6. Stop Criteria

Stop the pilot and record a no-go or incident when any of the following occurs:

- Any attempt to upload real sales data during L3.
- Any potential exposure of sensitive information.
- Calculation result mismatch or unexplained KPI inconsistency.
- Excel download failure that cannot be resolved by retrying normal operation.
- Streamlit access failure for approved pilot users.
- Access by an unauthorized user.
- Report text that could mislead a business decision.
- Any request to change formulas, loosen tests, or infer close days from weekday,
  date pattern, or `day_name` during the pilot.

## 7. Required Pilot Flow

Each pilot run should cover the following flow:

1. Select a sample or anonymous input case.
2. Confirm `is_close_day` is the only close-day decision field.
3. Confirm `day_name` is display-only.
4. Upload the input file or select the sample.
5. Review validation messages.
6. Review KPI and target status.
7. Review `target_variance` and `surplus_to_target`.
8. Review next-close cumulative-line required amount.
9. Review Scenario Grid.
10. Review P1/P2/P3 or O1/O2/O3 strategy output.
11. Review report text.
12. Download and inspect the Excel report.
13. Confirm whether forecast history was saved.
14. Review Backtest tab behavior.
15. Complete the pilot feedback form.

## 8. L4-Shadow And L4-Production Transition Conditions

L4-Shadow transition is allowed only as restricted internal aggregate
validation when all of the following are true:

- Deploy source clean local commit is recorded.
- Restricted internal invited users only.
- Password gate is maintained.
- Current input columns only.
- Aggregate target and cumulative performance values only.
- Aggregate monthly final_actual values only under LOCKE ownership.
- No identifiers in `memo`, file names, feedback, screenshots, or outputs.
- App results do not replace official operating judgment or reporting.
- Public broad real-data use remains prohibited.

L4-Production remains blocked until all of the following are approved and
evidenced:

- Remote HEAD is verified.
- Push and Streamlit redeploy are performed and verified.
- Private or restricted internal deployment is confirmed.
- Production access control is approved.
- Production real-data policy is approved.
- Official `final_actual` governance is approved.
- Password and secret rotation is confirmed.
- Official production approver is recorded.

R03 does not approve L4-Shadow or L4-Production. R04B approves only the
L4-Shadow policy structure and LOCKE-owned restricted aggregate data scope.

## 9. Known R03 Warnings

The following warnings are accepted only for L3 pilot preparation and must remain
visible in readiness records:

- Deploy source dirty state was a known R03 warning. R04A later recorded deploy
  source clean local commit
  `5be44e16b31da425d0e6fab326781a01581af25e`.
- Remote HEAD is not verified due to blocked network verification.
- Optional internal reviewer name is not recorded unless separately approved.
- Real sales data is not approved for L3.
- Restricted aggregate real-data is allowed only in L4-Shadow under LOCKE
  approval.
- Public broad real-data use is not approved.
- L3 `final_actual` real operation is not approved.
- L4-Shadow aggregate monthly final_actual is allowed only under LOCKE
  ownership.
- L4-Production is not approved.
- R03.1A launch approval final decision is `CONDITIONAL_GO`.

## 10. Pilot Exit Decision

At pilot end, LOCKE records one decision:

- `go`: continue or expand the internal pilot under the same data restrictions.
- `conditional_go`: proceed only after named conditions are resolved.
- `no_go`: pause until blockers are corrected.

The exit decision must include evidence references, remaining risks, and whether
L4 blockers are still open.
