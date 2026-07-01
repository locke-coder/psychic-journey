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

## Public Sharing

Do not use real operational sales data in a public or externally shared app.
Public demos must use anonymous or sample data only.

## Repository And Audit Policy

Real sales data and operator-saved defaults must not be committed to GitHub or
included in audit submission packages. `runtime_storage/`, `operator_data/`,
`local_data/`, `*.local.csv`, and `*.local.xlsx` are excluded by default.
