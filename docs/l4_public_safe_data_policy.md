# L4 Public Safe Data Policy

## 1. Purpose

This policy defines the data boundary for using the Streamlit month-end sales
forecast tool through a Public URL.

The user has confirmed the operating policy that the current app can be
accepted as Public because the app itself does not identify the company,
customers, organizations, contracts, phone numbers, addresses, or individuals.

Public use is allowed only for the app itself and sample, anonymous, or
non-identifying aggregate data. Real operational data and sensitive information
must not be uploaded to the Public URL.

## 2. Release Identity

- release_commit: `70139e39c25f12749c92b8906266dac8a26e8c89`
- app_url_primary:
  `https://locke-coder-psychic-journey-app-cxfzqk.streamlit.app/`
- app_url_alias: `https://sales-closing-forecast.streamlit.app/`
- audit_package: `audit_submit.zip`
- public_safe_policy_status: `defined`

## 3. Public URL Allowed Scope

The Public URL may be used only for:

- the Streamlit app UI itself
- bundled sample data
- anonymous data
- non-identifying aggregate data
- data that cannot identify the company, customers, individuals, contracts, or
  internal organizations even if externally disclosed

The Public URL must not be treated as a place for production operating data.
If a dataset would expose company, customer, person, contract, or organization
identity, it is outside the Public Safe scope.

## 4. App Identification Review

The R09-P review treats the app as Public Safe because:

- the app title and UI are generic sales-closing forecast wording
- no company name was identified in the app-facing strings reviewed
- no customer name was identified in the app-facing strings reviewed
- no organization name, branch name, center name, contract number, phone number,
  address, resident registration number, or account number was identified in
  the sample files reviewed
- sample files use schedule, close-day flags, aggregate targets, cumulative
  actuals, and generic memo text only

Generic business terms such as sales, recognized, close day, contract quality,
payment completion, cancellation, withdrawal, and unpaid risk are allowed when
they do not identify a real company, customer, contract, person, branch, or
center.

## 5. Allowed Upload Data

Only the following data may be uploaded to the Public URL:

- sample data
- anonymous data
- non-identifying aggregate daily target data
- non-identifying aggregate cumulative actual data
- non-identifying aggregate recognized target or actual data
- memo text that contains no company, customer, person, contract, branch,
  center, address, phone, account, or secret value

Allowed data must still follow the required input columns in `AGENTS.md`.
The close-day rule remains unchanged: close days are determined only by
`is_close_day`, and `day_name` is display-only.

## 6. Prohibited Upload Data

The following must not be uploaded, entered in `memo`, included in filenames,
captured in screenshots, or included in Excel reports shared outside the
approved scope:

- customer names / 고객명
- phone numbers / 전화번호
- addresses / 주소
- contract numbers / 계약번호
- resident registration numbers / 주민번호
- account numbers / 계좌번호
- responsible person or manager names / 담당자명
- branch names, center names, department names, or other organization
  identifiers / 지점명, 센터명, 부서명 등 조직 식별 가능 정보
- company-identifying terms when the dataset can reveal the company
- raw figures classified as internal sales secrets / 내부 영업기밀로 분류된
  원본 수치
- customer-level or contract-level transaction ledgers
- raw CRM exports
- passwords, API keys, tokens, private keys, or Streamlit secrets values

If any prohibited field is present, the file is not Public Safe.

## 7. Data Owner Approval

Before any non-sample operational dataset is considered, the data owner must
confirm that the dataset is anonymous or non-identifying.

The approval record should be stored outside this repository and should record:

- data owner or delegate
- approval date
- dataset name or business description
- confirmation that prohibited fields are absent
- approved upload users
- approved sharing scope for downloaded Excel files

Real customer, contract, person, organization, or internal secret data remains
blocked from the Public URL even if the data owner approves general testing.

## 8. User Confirmation Before Data Entry

Before uploading or entering data in the Public app, the user must confirm:

```text
I confirm that this file contains only sample, anonymous, or non-identifying
aggregate data. It does not contain customer names, phone numbers, addresses,
contract numbers, resident registration numbers, account numbers, responsible
person names, branch or center names, internal sales secrets, passwords, API
keys, tokens, or Streamlit secrets values.

이 파일은 샘플, 익명, 또는 비식별 집계 데이터만 포함합니다. 고객명,
전화번호, 주소, 계약번호, 주민번호, 계좌번호, 담당자명, 지점명, 센터명,
내부 영업기밀, 비밀번호, API key, token, Streamlit secrets 값을 포함하지
않습니다.
```

If the user cannot confirm this statement, the file must not be uploaded.

## 9. Excel Download And Sharing Policy

Excel reports downloaded from the Public app may be shared only when the input
data was Public Safe.

Excel files must not be:

- shared publicly if they contain real operational data
- attached to public issues, tickets, or repositories
- sent to unapproved external recipients
- used as evidence if prohibited fields are present
- retained after a prohibited-data incident without data owner approval

If an Excel report was generated from non-identifying sample or anonymous data,
it may be used for demo, QA, audit, or training within the approved sharing
scope.

## 10. Incident Stop, Delete, And Reverify Rule

Use of the Public app must stop immediately if:

- real operational data is uploaded to the Public URL
- company, customer, contract, person, branch, or center identifiers appear in
  input, memo, screenshot, logs, or Excel output
- secrets, keys, passwords, or tokens are entered or exposed
- an Excel report generated from prohibited data is downloaded or shared
- import, module, or secrets errors appear in deployment evidence
- the app begins displaying company-identifying or customer-identifying content

After an incident:

- stop using the affected app session and files
- delete affected uploads, screenshots, and Excel outputs from circulation
- remove shared links or attachments
- notify the data owner and security reviewer
- rerun the relevant security and smoke checks
- restart use only after the data owner records a new approval decision

## 11. Current Public Safe Decision

- public_allowed: `true`
- allowed_scope: `app_ui_and_sample_anonymous_non_identifying_data_only`
- real_data_public_upload_status: `blocked_by_policy`
- technical_upload_gate_changed: `false`
- app_code_changed_for_this_policy: `false`
- tests_changed_for_this_policy: `false`
- secrets_viewed_or_changed: `false`
- github_push_or_streamlit_redeploy: `false`
