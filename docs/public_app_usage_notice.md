# Public App Usage Notice

This Streamlit app is approved for Public URL use only with sample, anonymous,
or non-identifying aggregate data.

## Required User Notice

Before using the Public app, users must follow these rules:

- Use only sample, anonymous, or non-identifying aggregate data.
- Do not upload real operational data unless the data owner has confirmed that
  the file is non-identifying and approved for this Public Safe use.
- Do not enter customer names, phone numbers, addresses, contract numbers,
  resident registration numbers, account numbers, responsible person names,
  branch names, center names, or other information that can identify a company,
  customer, person, contract, or organization.
- Do not enter 고객명, 전화번호, 주소, 계약번호, 주민번호, 계좌번호, 담당자명,
  지점명, 센터명, or other organization-identifying information.
- Do not enter, paste, upload, screenshot, or expose passwords, API keys,
  tokens, private keys, `.streamlit/secrets.toml` values, or other secrets.
- Keep downloaded Excel files within the approved sharing scope.
- Do not attach Excel files generated from real or sensitive data to public
  issues, repositories, tickets, chat rooms, or external emails.
- Treat the forecast, scenario, and Excel outputs as decision-support material.
  Review the inputs, assumptions, and generated text before final reporting.

## Data Entry Confirmation

Before upload or manual entry, the user must be able to confirm:

```text
This data is sample, anonymous, or non-identifying aggregate data. It does not
contain customer, personal, contract, organization, address, phone, account,
internal sales secret, password, token, API key, or Streamlit secrets values.

이 데이터는 샘플, 익명, 또는 비식별 집계 데이터입니다. 고객명, 전화번호,
주소, 계약번호, 주민번호, 계좌번호, 담당자명, 지점명, 센터명, 내부 영업기밀,
비밀번호, token, API key, Streamlit secrets 값을 포함하지 않습니다.
```

If this confirmation is not true, do not use the Public app for that file.

## Downloaded Excel Files

Downloaded Excel reports inherit the sensitivity of the input data.

- Sample or anonymous inputs produce shareable demo or QA outputs within the
  approved scope.
- Non-identifying aggregate inputs may be shared only with approved recipients.
- Any file containing prohibited identifiers or secrets must be deleted from
  circulation and reviewed before reuse.

## Stop Conditions

Stop using the Public app and escalate to the data owner if:

- prohibited identifiers are found in an input, memo, screenshot, or Excel file
- real operational data was uploaded by mistake
- a downloaded file was shared outside the approved scope
- a secret, key, token, or password was entered or displayed
- the app shows import, module, or secrets errors

After a stop condition, delete affected artifacts from circulation and rerun the
readiness/security checks before resuming use.
