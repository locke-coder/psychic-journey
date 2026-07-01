# L4 Real Data Approval Control

## 1. Purpose

This document defines the approval and control requirements before any real
operational data is uploaded to the Streamlit month-end sales forecast tool.

The current release status is `L4_READY_PACKAGE_ONLY`. Real data upload remains
blocked until private or restricted deployment and release commit reflection are
verified.

## 2. Release Identity

- release_commit: `70139e39c25f12749c92b8906266dac8a26e8c89`
- app_url_primary:
  `https://locke-coder-psychic-journey-app-cxfzqk.streamlit.app/`
- app_url_alias: `https://sales-closing-forecast.streamlit.app/`
- audit_package: `audit_submit.zip`
- current_release_status: `L4_READY_PACKAGE_ONLY`

## 3. Required Approvals Before Real Data Use

Real data use requires documented approval before upload.

| Control item | Required owner or rule | Status |
| --- | --- | --- |
| Data owner approval | LOCKE or named business data owner | Required before upload |
| Security approval | LOCKE or approved internal security reviewer | Required before upload |
| App access approval | LOCKE confirms private/restricted deployment | Required before upload |
| Operator approval | Upload users must be named in a separate operating record | Required before upload |
| Final acceptance | L4 readiness evidence must be reviewed before production use | Required before upload |

Approver names, dates, and authorized user emails should be recorded in a
separate operating approval record, not in this repository document.

## 4. Authorized Upload Users

Only approved internal users may upload files. The approved list must be kept
outside this repository and must include:

- user name or internal identifier
- business role
- approval date
- access expiry or review date
- approval owner

Users not on the approved list must not upload operational data.

## 5. Allowed File Scope

Only aggregate month-end forecast input files are allowed after approval.

Allowed file scope:

- files using the required input columns defined in `AGENTS.md`
- aggregate daily sales targets
- aggregate daily recognized targets
- aggregate cumulative sales actuals
- aggregate cumulative recognized actuals
- non-identifying operational memo text only

The original source file must not be modified by the tool.

## 6. Prohibited Data

The following data must not be uploaded, stored, entered in `memo`, included in
file names, captured in screenshots, or shared through Excel outputs:

- customer names
- phone numbers
- addresses
- contract numbers or detailed contract identifiers
- resident registration numbers
- account numbers
- customer-level transaction ledgers
- contract-level transaction ledgers
- raw CRM exports
- employee personal information
- passwords, API keys, tokens, private keys, or secrets

If any prohibited field appears in an input, output, screenshot, feedback item,
or attachment, use must stop immediately and the affected artifact must be
removed from circulation.

## 7. Public URL Rule

Real data upload to a public URL is prohibited.

If private or restricted deployment is not verified, the app must be treated as
public for real-data purposes even when the URL is only known internally.

Real data may be considered only after one of the following access-control
models is verified:

- Streamlit private app
- team-only access
- authorized users only
- SSO or organization access
- approved internal network, VPN, or proxy access control

## 8. Excel Output Sharing

Excel reports generated from approved real data must be shared only with the
approved internal operating group.

Excel outputs must not be:

- posted to public links
- sent to unapproved external recipients
- attached to public tickets or issues
- stored in repositories
- used as evidence if they contain prohibited identifiers

## 9. Retention And Deletion

Operational files and generated outputs must follow the approved retention
period set by the data owner.

Minimum deletion requirements:

- remove rejected or contaminated uploads immediately
- remove outputs created from rejected or contaminated inputs immediately
- delete access for users who leave the operating role
- review retained files after the month-end close period
- keep only approved audit records needed for traceability

No `.streamlit/secrets.toml`, `.env`, key file, password, token, or private key
may be copied into retention folders or audit packages.

## 10. Incident Response

Immediately stop use and escalate to LOCKE or the named data owner if any of
the following occurs:

- real data is uploaded before access approval
- the app is found to be public while real data is intended
- prohibited fields appear in input, output, memo, screenshot, or file name
- secrets, keys, or passwords are exposed
- unauthorized users can access the app or outputs
- import, module, or secrets errors appear in deployment logs
- generated Excel outputs are shared outside the approved group

After an incident:

- stop app use for affected data
- delete affected uploads and outputs
- remove shared links or attachments
- rerun the relevant audit checks
- document the incident, remediation, and approval decision before restart

## 11. Current Decision

- approval_doc_created: `true`
- data_owner_required: `true`
- upload_users_defined: `required externally before upload`
- prohibited_fields_defined: `true`
- public_url_real_data_blocked: `true`
- retention_deletion_policy_defined: `true`
- excel_sharing_policy_defined: `true`
- real_data_uploaded_in_R09: `false`
- current_real_data_upload_status: `blocked until private/restricted deployment and commit reflection are verified`
