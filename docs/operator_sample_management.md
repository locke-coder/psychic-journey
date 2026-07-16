# Operator Sample Management

## Purpose

The app can keep operator-managed default input samples outside `data/sample`.
This lets an operator update the default current-month input table and the
historical comparison table from the Streamlit screen without editing packaged
fixtures or redeploying the app.

## Packaged Sample Vs Operator Storage

`data/sample/` is the packaged, version-controlled sample and test fixture
area. It must remain safe for audit and automated tests.

`runtime_storage/operator_samples/` is runtime data created by the running app.
When an operator saves a default sample, the app writes CSV files there:

- `current_input_sample.csv`
- `historical_input_sample.csv`
- `metadata.json`
- `backups/*.csv`

If `OPERATOR_SAMPLE_DIR` is set, the app uses that directory instead of the
default runtime path.

## Saving From The App

Open the input page and expand **운영 샘플 관리**.

For the current input sample, edit the table and click
**현재 입력값을 운영 기본값으로 저장**.

For the historical sample, edit the table and click
**과거 샘플을 운영 기본값으로 저장**.

Uploaded files are only session working data until one of those save buttons is
clicked.

## Restore On App Restart

At startup, the app loads operator storage first. If the operator CSV exists
and passes validation, it becomes the default table. If it is missing or broken,
the app falls back to the packaged `data/sample` CSV.

## Returning To Packaged Samples

Use **내장 샘플로 화면 초기화** to reload the packaged sample into the current
screen. This does not overwrite operator storage. To make the packaged sample
the future default, click the relevant save button after the screen reset.

Use **저장된 운영 기본값 다시 불러오기** to return the screen to the latest
operator-saved CSV.

## Backups

Before replacing an existing operator CSV, the app writes a timestamped backup
under:

`runtime_storage/operator_samples/backups/`

The app keeps the newest backup files for each sample kind and prunes older
ones.

## Multi-User Note

Operator storage is an app-wide default. If multiple users share the same app
instance, a saved operator sample affects the default loaded by everyone after
restart or reload.

## Ephemeral Filesystems

Some platforms, including Streamlit Community Cloud-style environments, may
reset the local filesystem during redeploys or restarts. For durable production
operation in those environments, use an external store such as a database, NAS,
S3-compatible storage, or a controlled Google Sheet.

## GitHub External Store

For Streamlit Cloud-style hosting, the app can use a separate private GitHub
repository as the durable data store. Prefer these Streamlit Secrets or
environment variables:

- `PRIVATE_DATA_REPO`: private repository in `owner/name` format
- `PRIVATE_DATA_TOKEN`: fine-grained token limited to that repository
- `PRIVATE_DATA_BRANCH`: defaults to `main`
- `PRIVATE_DATA_PREFIX`: defaults to `operator_samples`

The legacy `GITHUB_OPERATOR_SAMPLE_*` names remain supported.

When configured, the app uses the repository for operator inputs, saved actuals,
forecast history, final actuals, and generated reports:

```text
operator_samples/current_input_sample.csv
operator_samples/historical_input_sample.csv
operator_samples/metadata.json
operator_samples/actuals/saved_actuals.csv
operator_samples/history/forecast_history.csv
operator_samples/history/final_actuals.csv
operator_samples/reports/latest/
```

Use a private repository only. GitHub commit history keeps previous versions, so
do not store unapproved personal or sensitive sales data there.

## Public Sharing

Do not use real operational sales data in a public or externally shared app.
Public demos must use anonymous or sample data only.

## Repository And Audit Policy

Real sales data and operator-saved defaults must not be committed to the public
code repository or included in audit submission packages. They may be stored
only in the approved private data repository. `runtime_storage/`, `operator_data/`,
`local_data/`, `*.local.csv`, and `*.local.xlsx` are excluded by default.
