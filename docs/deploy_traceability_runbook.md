# Deploy Traceability Runbook

## Purpose

This runbook defines how to identify which local code, generated outputs, and
Streamlit deploy source should be used for L3 internal pilot operation,
L4-Shadow validation, and L4-Production release.

R01 does not change forecast, provision, overachievement, scenario, report, history, final actual, backtest, or Streamlit app calculation behavior. Close-day logic remains based only on the `is_close_day` column. `day_name` is display-only.

## Repository Layout

- Local app root: the working application source directory.
- Deploy source: `outputs/streamlit_deploy_source`.
- Shareable latest outputs: `outputs/latest`.
- Old workbook format archive: `outputs/archive_old_format`.
- Invalid workbook archive: `outputs/archive_invalid`.

The deploy source is a separate Git repository used as the Streamlit deployment package. It can have its own branch, HEAD, remote, and dirty state.

## Local and Deploy Hash Check

Run:

```powershell
.\.venv\Scripts\python.exe tools\check_deploy_traceability.py --l3
```

For JSON:

```powershell
.\.venv\Scripts\python.exe tools\check_deploy_traceability.py --json
```

The tool compares deployment-relevant files between the local app root and `outputs/streamlit_deploy_source`.

Strict runtime comparison includes:

- `app.py`
- `requirements.txt`
- `README.md`
- `src/**/*.py`
- runtime `config/*.yaml`
- `data/sample/*.csv`
- `.streamlit/config.toml`

`config/gate_audit_catalog.yaml` is treated as audit trace metadata, not a Streamlit runtime calculation file. It is still reported when it differs, but it does not turn runtime hash matching into a calculation deployment mismatch.

Optional trace comparison includes shared docs, audit catalog, and tools that exist in both locations. Optional local-only docs or audit tools are reported separately as missing optional files, not hidden.

## Deploy Dirty State

`deploy_dirty: true` means the deploy source Git repository has uncommitted or untracked changes. This is acceptable only as a recorded L3 warning when the core file hash comparison matches.

For L4-Shadow and L4-Production, dirty deploy source is not acceptable. The
deploy source must be clean so the deployed package can be traced to a recorded
commit.

R04A deploy source clean local commit:
`5be44e16b31da425d0e6fab326781a01581af25e`.

R04B does not perform push, Streamlit redeploy, or remote HEAD verification.

## Remote HEAD Verification

The traceability tool attempts to verify the remote HEAD when possible. If TLS, certificate, authentication, or network errors block the check, the tool records `remote_head_verified: false` and a `remote_head_error_type`.

Interpretation:

- L3: remote HEAD failure can be carried as a known warning when local/deploy hashes match.
- L4-Shadow: remote HEAD failure remains a recorded risk because shadow access
  is restricted and app output is not official reporting.
- L4-Production: remote HEAD failure is a release blocker.

The tool must not turn remote verification failure into a forced PASS.

## Streamlit Pre-Deploy Checklist

1. Run full pytest.
2. Run Gate Runner `ALL`.
3. Run `tools/check_outputs_latest.py --strict`.
4. Run `tools/check_deploy_traceability.py --l3`.
5. Confirm `outputs/latest` contains only current reports, valid input templates, and `.gitkeep`.
6. Confirm local/deploy core file hashes match.
7. Record deploy branch, HEAD, dirty state, and remote HEAD verification result.
8. Use only anonymous or sample data for L3.
9. For L4-Shadow, use only LOCKE-approved aggregate inputs and maintain the
   password gate.

## Files Never Included

Never include, print, copy into shared outputs, or deploy these files:

- `.streamlit/secrets.toml`
- `.env`
- `*.key`
- Real sales data outside the approved L4-Shadow aggregate scope
- Real customer or employee data
- History files containing operational real data unless an approved retention and access policy exists

## L3 vs L4-Shadow vs L4-Production

L3 internal pilot can proceed with:

- pytest PASS
- Gate Runner ALL PASS
- `outputs/latest` strict PASS
- local/deploy core hash MATCH
- deploy dirty state recorded as a known warning
- remote HEAD failure recorded as a known warning
- anonymous or sample data only
- restricted pilot users

L4-Shadow can proceed conditionally with:

- pytest PASS
- Gate Runner ALL PASS
- `G23_OUTPUTS_LATEST_STRICT` PASS
- `outputs/latest` strict PASS
- deploy source clean local commit recorded
- restricted internal invited users only
- current input columns only
- aggregate target and cumulative performance values only
- aggregate monthly final_actual values only under LOCKE ownership
- no identifiers in `memo`, file names, feedback, screenshots, or outputs
- password gate maintained
- no external sharing
- app output not used as official reporting

L4-Production requires:

- clean deploy source
- remote HEAD verified
- deploy commit hash recorded
- private or internal-network deployment
- access controls confirmed
- password and secret rotation procedure confirmed
- real-data storage and sharing policy approved
- final actual operation procedure approved

L4-Production is not approved by R04B.
