# Private Data Store Runbook

## Purpose

The application code repository and the durable data repository are separate.
The code repository may be public only when it contains no operational data or
secrets. The data repository must remain private and accessible only to the app
runtime and approved administrators.

This storage change does not make the deployed app private by itself. App
visibility and user authentication must still be restricted separately before
real operational data is used.

## Required secrets

Configure these values in Streamlit Secrets or an approved secret manager. Do
not put their real values in this repository.

```toml
PRIVATE_DATA_REPO = "owner/private-data-repo"
PRIVATE_DATA_TOKEN = "replace_me"
PRIVATE_DATA_BRANCH = "main"
PRIVATE_DATA_PREFIX = "operator_samples"
PRIVATE_DATA_TIMEOUT_SECONDS = 10
PRIVATE_DATA_MODE = "private"
```

The existing `GITHUB_OPERATOR_SAMPLE_*` names remain supported for a gradual
cutover. When both sets exist, `PRIVATE_DATA_*` takes precedence.

`PRIVATE_DATA_MODE` defaults to `private`, so a missing repository or token
stops the app. `local_demo` is the only mode that permits packaged/local sample
storage and must be selected explicitly for isolated demo or development use.

Use a fine-grained token limited to the single private data repository with the
minimum repository contents permission required to read and write files. Rotate
the token periodically and immediately after suspected exposure.

## Durable paths

All paths below are relative to `PRIVATE_DATA_PREFIX`.

```text
current_input_sample.csv
historical_input_sample.csv
metadata.json
actuals/saved_actuals.csv
history/forecast_history.csv
history/final_actuals.csv
reports/latest/daily_report_*.xlsx
reports/latest/daily_report_*.xlsx.manifest.json
```

Uploaded files and Excel build files may exist only in process-scoped temporary
directories. They are not durable storage and are deleted after processing.
Passwords and access tokens remain in the secret manager, never in the data
repository.

## Failure and concurrency behavior

- A partial repository/token configuration stops Private-store operations.
- When Private storage is configured, a missing, inaccessible, or invalid
  current input does not fall back to a packaged or local sample.
- Current input, saved actuals, and metadata are published in one Git commit.
- Excel and its SHA-256 manifest are published in one Git commit.
- Single CSV updates use the previously read blob SHA. A concurrent update is
  rejected and must be retried after reloading current data.
- Error messages do not include token values or GitHub response bodies.

## One-time migration

Run the migration tool without `--apply` first. It prints only path, byte count,
row count where applicable, and SHA-256; it never prints data values.

```powershell
.\.venv\Scripts\python.exe tools\migrate_private_data_store.py
.\.venv\Scripts\python.exe tools\migrate_private_data_store.py --apply
```

The apply step refuses to replace a different remote file unless
`--replace-existing` is explicitly supplied. It uploads all changed files in a
single commit and reads them back to verify byte-for-byte hashes. Local source
files are not deleted automatically.

After successful verification:

1. Confirm the app reads the Private-store versions.
2. Confirm save conflicts are reported rather than overwritten.
3. Remove operational files from the public code repository's Git index and
   rotate any secret that may ever have been committed.
4. Preserve only approved anonymous templates and sample data in the code repo.

## Rollback

Revert the data repository branch to the last approved commit through the
private repository's controlled administrator workflow. Do not disable the
Private-store secrets to force a packaged-data fallback in production. If the
store is unavailable, stop writes, restore access, and re-run read verification.
