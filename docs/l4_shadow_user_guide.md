# L4-Shadow User Guide

Created: 2026-06-12 KST.

## Purpose

Use the app only for restricted internal L4-Shadow validation. The app runs in
parallel with the existing operating process and does not replace official
reporting or closing decisions.

## Access

- Use only the approved Streamlit URL shared through the internal launch
  channel.
- Do not forward the URL, password/auth instructions, Excel output, or reports.
- If access appears public or is available to an unapproved user, stop and
  notify LOCKE.

## Allowed Input Data

Use only aggregate input columns:

- `date`
- `day_name`
- `business_day_no`
- `is_close_day`
- `close_type`
- `sales_target_daily`
- `recognized_target_daily`
- `sales_actual_cum`
- `recognized_actual_cum`
- `memo`

## Prohibited Input Data

Do not enter or upload:

- Customer names.
- Phone numbers.
- Addresses.
- Contract numbers.
- Resident registration numbers.
- Personal identifying information.
- Customer-level or contract-level ledgers.
- Raw CRM exports.
- Secrets, keys, or passwords.

## Memo Rules

- Write only non-identifying operating notes.
- Do not include customer, contract, person, address, phone, or account
  details.
- Do not put identifiers in file names.

## Result Interpretation

Target status:

- `UNDER_TARGET`: Target correction or recovery action needs review.
- `ON_TARGET`: Maintain and monitor.
- `OVER_TARGET`: Manage overachievement quality and sustainability.

Overachievement strategies:

- `O1`: Maintain buffer.
- `O2`: Convert to Stretch.
- `O3`: Defend quality.

Provision strategies:

- `P1`, `P2`, and `P3` should be reviewed with the Scenario Grid and Report
  Text before any operating comparison is recorded.

## Excel Download

- Download Excel only for approved internal shadow validation.
- Do not share externally.
- Do not rename files with identifiers.
- Excel output is not an official production report during L4-Shadow.

## Feedback

Submit feedback after each shadow execution. Do not include personal data,
customer data, contract data, passwords, keys, or real customer examples in the
feedback form.

## Important Reminder

L4-Shadow results are validation evidence only. Continue using the official
operating and reporting process as the source for production decisions.
