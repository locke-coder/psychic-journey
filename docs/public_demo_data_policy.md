# D06-B Public Demo Data Policy

## Scope

This policy applies to the L3 public demo and any L3 private pilot preparation before private QA is complete.

## Allowed Data

- Public Streamlit URLs may use only sample or anonymized data.
- `outputs/latest` may contain only public/sample artifacts prepared for review.
- Demo screenshots and downloaded files must be created from sample or anonymized inputs only.

## Prohibited Data

- Do not upload real operating data to the public Streamlit app.
- Do not include customer names, phone numbers, addresses, contract numbers, resident registration numbers, or other sensitive identifiers in sample files, tests, docs, logs, screenshots, audit packages, or downloads.
- Do not copy private inputs, private outputs, or private screenshots into the repository, `outputs/latest`, `audit_submit`, or `audit_submit.zip`.
- Do not operate L4 private real data mode until private QA and explicit approval are complete.

## Secrets

- `.streamlit/secrets.toml`, `.env`, `*.key`, and secret-bearing files must not be committed or packaged.
- If secrets are needed for a hosted deployment, enter them directly in Streamlit Cloud Advanced settings.
- Do not print or capture secret values in logs, screenshots, docs, or audit artifacts.

## Stop Conditions

Stop the deployment immediately if any sensitive data is found in demo mode, source artifacts, logs, screenshots, `outputs/latest`, `audit_submit`, or `audit_submit.zip`.

## UI Notice Requirement

The public demo must display a security warning in the sidebar or footer that the app accepts sample/anonymized data only and that real operating data must not be uploaded.
