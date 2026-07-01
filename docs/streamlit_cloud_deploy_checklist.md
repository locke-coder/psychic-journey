# Streamlit Cloud Deploy Checklist

## Deployment Level

- Target: `L3_PUBLIC_DEMO`
- Allowed data: sample/anonymized data only
- Real/private operating data: prohibited
- L4 private real data: prohibited until private QA approval

## Repository Readiness

- [ ] GitHub repository is ready for Streamlit Community Cloud.
- [ ] Main file path is `app.py`.
- [ ] `requirements.txt` exists.
- [ ] `requirements.txt` includes `streamlit`, `pandas`, `openpyxl`, `altair`, `pyyaml`, and `pytest`.
- [ ] Public repo contains no private input, output, or screenshot artifacts.
- [ ] Public repo contains no real customer names, phone numbers, addresses, contract numbers, resident registration numbers, or other sensitive identifiers.

## Secrets Policy

- [ ] `.streamlit/secrets.toml` is not committed.
- [ ] `.streamlit/secrets.toml` is not included in `audit_submit` or `audit_submit.zip`.
- [ ] `.env` is not committed or packaged.
- [ ] `*.key` files are not committed or packaged.
- [ ] `*secret*` or `*secrets*` files are excluded unless they are safe placeholders such as `.streamlit/secrets.example.toml`.
- [ ] Required hosted secrets, if any, are entered only through Streamlit Cloud Advanced settings.
- [ ] Secret values are not printed in logs, docs, screenshots, or reports.

## Streamlit Cloud Manual Steps

- [ ] Open Streamlit Community Cloud.
- [ ] Select the workspace for the demo app.
- [ ] Choose Create app.
- [ ] Select the GitHub repository and branch.
- [ ] Set the main file path to `app.py`.
- [ ] Confirm Advanced settings contain no real data and no unintended secrets.
- [ ] Deploy.
- [ ] Verify the public URL opens with sample/anonymized data only.

## Post-Deploy Evidence

- [ ] Save the deployed URL in the D06-B readiness record.
- [ ] Capture QA screenshots using sample/anonymized data only.
- [ ] Store screenshot evidence in the approved evidence location.
- [ ] Do not upload private data to the public URL during QA.
