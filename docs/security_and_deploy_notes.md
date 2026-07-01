# Security And Deploy Notes

Updated for R04B on 2026-06-11 KST.

## Local Operation Vs Deployment

The app supports month-end forecasting by allowing users to enter operating
dates, daily targets, cumulative performance values, and non-identifying memos.
Local operation and deployed operation have different risk profiles because
deployment introduces viewer access, shared outputs, retention, and audit
requirements.

## U02 Local Audit Auth Gate Status

U02 temporarily disables the runtime password/Auth Gate for local audit and
screen capture convenience. This is not an approval for external operation.
Before Public or external deployment, R01 must restore an Auth Gate and verify
access-control behavior.

`.streamlit/secrets.toml` remains local-only. Its contents must not be read,
printed, copied, reported, or included in audit/deployment packages.

Real operational data, customer identifiers, contract identifiers, and person
level data must not be exposed outside the approved internal process.

## Stage-Based Data Policy

| Stage | Data policy | Deployment posture |
| --- | --- | --- |
| L3 | Sample / anonymous only | Current Streamlit URL plus password gate for approved internal pilot users. |
| L4-Shadow | Restricted internal aggregate real-data shadow validation | Invited internal users only, password gate maintained, no external sharing. |
| L4-Production | Official production operation | Not approved until remote HEAD, access control, final_actual governance, and official approval are complete. |

The L3 "sample / anonymous only" rule remains valid for L3. R04B adds
L4-Shadow as a separate restricted stage where aggregate real-data-like inputs
are allowed under LOCKE approval. Public broad real-data use remains
prohibited.

## Public Streamlit Deployment

Public broad real-data use is prohibited. Do not upload operational real data,
customer data, contract data, person-level data, raw CRM exports, secrets, keys,
or passwords to a public or externally shared Streamlit URL.

Demo or L3 pilot use must remain sample or anonymous.

## Restricted Internal L4-Shadow Deployment

L4-Shadow may use the current Streamlit URL plus password gate and/or Streamlit
private invited users when all of the following are true:

- LOCKE approves the invited-user list.
- Viewer list is reviewed before launch.
- Access is removed after the shadow period or role change.
- Only current input columns are used.
- Only aggregate targets, aggregate cumulative actuals, aggregate recognized
  actuals, and aggregate monthly final_actual values are used.
- `memo` and file names contain no identifiers.
- Outputs and Excel downloads stay inside the approved internal shadow group.
- App results do not replace official reporting.

Actual invited-user email addresses are managed in a separate operating note and
are not recorded in this repository document.

## Secrets Management

Never include, print, copy, or package the following:

- `.streamlit/secrets.toml`
- `.env`
- `*.key`
- Passwords
- API tokens
- Private keys

Only placeholder examples may be shared, such as
`.streamlit/secrets.example.toml`.

## Real Data And Identifier Rules

Allowed during L4-Shadow:

- Aggregate daily target values.
- Aggregate cumulative actual values.
- Aggregate recognized cumulative actual values.
- Aggregate monthly final_actual values under LOCKE ownership.

Prohibited in all non-production repository documents, outputs, file names,
feedback, screenshots, and shared artifacts:

- Customer names.
- Phone numbers.
- Addresses.
- Contract numbers.
- Resident registration numbers.
- Employee personal information.
- Customer-level transaction ledgers.
- Contract-level transaction ledgers.
- Raw CRM exports.
- Secrets, keys, and passwords.

If an identifier is found in `memo`, a file name, output, screenshot, or
feedback item, remove the artifact from circulation and recreate the input or
evidence without the identifier.

## Audit Package Generation

Audit packages must not include secrets, invalid archives, raw CRM exports, or
customer/contract/person-level operational files. R04B does not regenerate
`audit_submit.zip`.

Runtime operator sample storage is also excluded from audit packages by
default. Do not include `runtime_storage/`, `runtime_storage/operator_samples/`,
`operator_data/`, `local_data/`, `*.local.csv`, or `*.local.xlsx` unless a
separate internal approval explicitly confirms that all real operational and
identifier-like data has been removed.

The audit manifest may record excluded runtime paths by name only. It must not
copy or summarize operator sample file contents.

## R04A Deploy Basis

- Deploy source clean local commit:
  `5be44e16b31da425d0e6fab326781a01581af25e`.
- Push performed in R04B: false.
- Streamlit redeploy performed in R04B: false.
- Remote HEAD verified in R04B: false.
