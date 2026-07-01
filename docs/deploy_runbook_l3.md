# L3 Internal Pilot Deploy Runbook

## Purpose

This runbook is for an L3 internal pilot of the Streamlit app in `app.py`.
It is not an L4-Production runbook.

The L3 pilot is limited to approved internal viewers and sample or anonymous
data only.

## Current GitHub Streamlit Target

- GitHub repository: `https://github.com/locke-coder/psychic-journey.git`
- Streamlit app URL: `https://locke-coder-psychic-journey-app-cxfzqk.streamlit.app/`
- Streamlit source URL: `https://share.streamlit.io/locke-coder/psychic-journey/main/app.py`
- Deploy branch: `main`
- Latest prepared deploy commit:
  `c126b8b7bc770f45b6399412ba293f9febd45f4d`
- Stage: L3 internal pilot
- Data policy: sample / anonymous only

The prepared commit was not pushed from Codex because GitHub access in this
environment required TLS certificate verification to be disabled while the
commit included allowed `outputs/latest` `.xlsx` artifacts. Push the prepared
commit from a trusted Git environment with normal certificate verification:

```powershell
git --git-dir outputs/push_bare_repo_20260625_001 push origin refs/heads/main:refs/heads/main
```

After manual push, confirm remote `main` equals:

```text
c126b8b7bc770f45b6399412ba293f9febd45f4d
```

Then verify the Streamlit app URL. If Streamlit does not pick up the GitHub
commit automatically, trigger a manual reboot or redeploy from the Streamlit
Cloud console.

## Data Policy

Allowed:

- Packaged sample data.
- Anonymous aggregate pilot inputs.
- Non-identifying memo text only.

Prohibited:

- Real customer names, phone numbers, addresses, resident IDs, contract IDs,
  customer-level ledgers, contract-level ledgers, and raw CRM exports.
- Real secrets, passwords, API tokens, private keys, `.env`, `*.key`, and
  `.streamlit/secrets.toml` in Git, audit packages, or deploy packages.
- Public broad real-data use.

## Pre-Deploy Checks

Run these checks from the project root:

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe tools\gate_runner.py ALL
Select-String -Path "src\*.py","app.py","tests\*.py" -Pattern "weekday|WEEKDAY|dt.weekday|date.weekday|next_monday|next_thursday|day_name ==|day_name in|월요일|목요일"
```

Required results:

- `pytest` passes.
- Gate Runner `ALL` passes.
- Source forbidden-pattern hits are `0`.
- Test-only forbidden-pattern guard/catalog hits may appear and must be
  reported separately.
- `.streamlit/secrets.toml`, `.env`, `*.key`, `runtime_storage/`,
  `runtime_storage/operator_samples/`, `operator_data/`, and `local_data/` are
  excluded from deploy and audit packages.
- `audit_submit.zip`, `audit_submit/`, `outputs/archive_invalid/`, and
  `outputs/archive_old_format/` are excluded from GitHub deploy commits.

## Local Or Internal Server Start

Use a persistent operator sample directory for an internal server:

```powershell
$env:OPERATOR_SAMPLE_DIR="D:\sales-closing-forecast\operator_samples"
$env:APP_ACCESS_PASSWORD="replace_with_approved_secret_from_secret_manager"
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true
```

For a one-time smoke test, use a temporary operator sample path:

```powershell
$env:OPERATOR_SAMPLE_DIR="$PWD\.tmp_operator_sample_deploy_smoke"
$env:APP_ACCESS_PASSWORD="replace_with_nonproduction_smoke_password"
.\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8515 --server.headless true
```

Do not use `runtime_storage/operator_samples` for smoke validation.

## OPERATOR_SAMPLE_DIR

`OPERATOR_SAMPLE_DIR` controls where operator-managed default samples are
stored.

- If set, the app uses that path.
- If unset, the app defaults to `runtime_storage/operator_samples`.
- The app loads operator storage first and falls back to `data/sample` when the
  operator CSV is missing, invalid, or broken.
- Uploaded files are session working data until an operator save button is
  clicked.
- Operator storage is an app-wide default for all users of the same app
  instance.

For durable internal operation, point `OPERATOR_SAMPLE_DIR` to a persistent
volume, NAS path, database-backed mount, or other approved internal storage.
Streamlit Community Cloud-style ephemeral filesystems do not guarantee
operator sample persistence.

## Secrets

`.streamlit/secrets.toml` is local-only. Do not read, print, copy, commit, or
package its contents.

For deployment, configure secrets through one of these approved mechanisms:

- Platform secret manager.
- OS environment variables.
- Internal secret manager injected into the runtime environment.

Do not document secret values in runbooks, tickets, audit logs, screenshots, or
Excel outputs.

## Platform Notes

### Streamlit Cloud-Style Hosting

- Use private, invite-only, or approved-viewer access.
- Do not push `.streamlit/secrets.toml`.
- Set secrets in the platform UI or approved secret manager.
- If the URL is public or externally reachable and access control is not
  verified, stop deployment.
- L3 remains sample or anonymous only.

### Internal Server Or VM

- Create or reuse a controlled virtual environment.
- Install `requirements.txt`.
- Set `OPERATOR_SAMPLE_DIR` to a persistent internal path.
- Start Streamlit behind VPN, SSO, reverse proxy authentication, or another
  approved access-control layer.
- Keep logs and outputs inside approved internal storage.
- Do not copy `.streamlit/secrets.toml` into deploy packages.

### Docker Or Volume-Based Deployment

- Mount a persistent volume for `OPERATOR_SAMPLE_DIR`.
- Inject secrets as environment variables or through the platform secret
  manager.
- Keep the container image free of `.env`, `*.key`, private keys, and local
  secrets files.
- Restrict network access to approved internal users.

## Smoke Test

After start, verify:

- HTTP 200 from the Streamlit endpoint.
- KPI/forecast screen loads.
- `ScenarioGrid` is visible.
- O1/O2/O3 overachievement strategies are present.
- Excel download works.
- Operator sample management expander is available.
- No secrets are printed in logs.

For Codex-local verification, HTTP 200 and server-alive checks are acceptable
when browser automation is unavailable.

## Rollback

Rollback triggers:

- `pytest` failure.
- Gate Runner failure.
- Source forbidden-pattern hit.
- Secret, `.env`, `*.key`, or operator runtime storage appears in the deploy
  package.
- Streamlit start failure.
- Public/external URL without verified access control.
- Any suspected real customer, contract, raw CRM, or identifier exposure.

Rollback actions:

- Stop the running Streamlit process or deployment.
- Revert to the previous approved zip, commit hash, branch, or internal server
  artifact.
- Restore operator sample storage from the latest approved backup if needed.
- Remove exposed outputs or screenshots from circulation.
- Re-run pre-deploy checks before resuming the pilot.

## L4 Transition Conditions

Do not treat L3 pilot completion as production approval. Before L4-Shadow or
L4-Production:

- Approved viewer list is documented and reviewed.
- Access removal procedure exists.
- Access control is verified.
- Real-data shadow inputs are aggregate-only and internally restricted.
- Outputs remain internal.
- `final_actual` governance is approved.
- Remote HEAD or deploy artifact baseline is traceable.
- Official approval is recorded.

L4-Production remains blocked until access control, governance, baseline
traceability, and official approval are complete.
