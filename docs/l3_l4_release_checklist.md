# L3 / L4-Shadow / L4-Production Release Checklist

R04B reframes release readiness into three stages:

- L3: sample / anonymous pilot.
- L4-Shadow: restricted internal aggregate real-data shadow validation.
- L4-Production: official production operation.

The existing L3 sample / anonymous restriction remains valid for L3. R04B adds
L4-Shadow as a controlled internal validation stage and does not approve
L4-Production.

## L3 Internal Pilot Criteria

- pytest PASS.
- Gate Runner `ALL` PASS.
- `G23_OUTPUTS_LATEST_STRICT` PASS.
- `outputs/latest` strict check PASS.
- Local app root and deploy source core file hashes MATCH.
- Deploy source dirty state may be accepted only as a recorded known warning for
  L3.
- Remote HEAD verification failure may be accepted only as a recorded known
  warning for L3.
- Only anonymous or sample data is used.
- Pilot access is limited to approved internal users.
- No `.streamlit/secrets.toml`, `.env`, `*.key`, real sales data, customer
  data, contract data, or personal data is shared through outputs or deploy
  packages.

## L4-Shadow Criteria

- pytest PASS.
- Gate Runner `ALL` PASS.
- `G23_OUTPUTS_LATEST_STRICT` PASS.
- `outputs/latest` strict check PASS.
- Deploy source clean local commit exists.
- R04A deploy source clean local commit is recorded:
  `5be44e16b31da425d0e6fab326781a01581af25e`.
- Restricted internal invited users only.
- Password gate maintained.
- Current input columns only.
- Aggregate daily targets, aggregate cumulative actuals, aggregate recognized
  actuals, and aggregate monthly final_actual values only.
- `memo` and file names contain no identifiers.
- Excel output is shared only inside the approved internal shadow group.
- App results do not replace official operating judgment, reporting, or closing
  decisions.
- Public broad real-data use is prohibited.
- L4-Production remains not approved.

## L4-Production Criteria

- Deploy source Git status is clean.
- Deployment commit hash is pushed and recorded.
- Streamlit redeploy is completed and verified.
- Remote HEAD verification succeeds.
- Streamlit deployment is private or restricted to approved internal access.
- Access rights are approved and tested.
- Password and secret rotation process is confirmed.
- Production real-data storage, retention, export, and sharing policy is
  approved.
- Official `final_actual` owner, cutoff date, correction authority, deletion
  authority, retention period, and audit log standard are approved.
- Rollback owner and rollback package are identified.
- Official production approver is recorded.

## Required Commands

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe tools\gate_runner.py ALL
.\.venv\Scripts\python.exe tools\gate_runner.py G23_OUTPUTS_LATEST_STRICT
.\.venv\Scripts\python.exe tools\check_outputs_latest.py --strict
.\.venv\Scripts\python.exe tools\check_deploy_traceability.py --l3
```

For L4-Production readiness:

```powershell
.\.venv\Scripts\python.exe tools\check_deploy_traceability.py --l4
```

## Release Record Template

- release date:
- release level: L3 / L4-Shadow / L4-Production
- local package hash:
- deploy source path:
- deploy branch:
- deploy commit:
- R04A deploy clean commit:
  `5be44e16b31da425d0e6fab326781a01581af25e`
- deploy dirty: true / false
- push performed: true / false
- redeploy performed: true / false
- remote HEAD verified: true / false
- Streamlit URL:
- pytest result:
- Gate Runner ALL result:
- G23 result:
- outputs/latest strict result:
- local/deploy hash match: true / false
- data scope: sample / anonymous / restricted aggregate shadow / production
- pilot, shadow, or production users:
- app result replaces official reporting: true / false
- known risks:
- approver:

## Known Risk Severity

- S1: Blocks L4-Production or invalidates traceability.
- S2: Allows L4-Shadow only with explicit owner and mitigation.
- S3: Operational warning that should be cleared before broad rollout.
- S4: Documentation or housekeeping issue with low operational impact.
