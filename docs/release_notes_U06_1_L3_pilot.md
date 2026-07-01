# U06.1 L3 Pilot Release Notes

## Baseline

- release_id: U06.1
- baseline_file: audit_submit_U06_1_latest_UPLOAD_THIS.zip
- sha256: 68a8c1da76da8c19e4a9faa974bedc9ee64bc5d1e35af77a8c08534249759191
- verdict: CONDITIONAL_PASS / L3 Pilot OK
- frozen_status: FROZEN_FOR_L3_PILOT
- frozen_at: 2026-06-17 KST

## Scope

U06.1 is frozen as the L3 pilot baseline. The baseline ZIP is not rebuilt, repacked, or edited.

- scope: 샘플/익명화 데이터 기반 내부 제한 파일럿
- pilot data: sample/anonymized data only
- production data: not allowed

## Allowed Use

- LOCKE 단독 로컬 운영
- 샘플/익명화 데이터 시연
- 1~3명 제한 내부 파일럿

## Not Allowed

- 실고객/실매출 원본 데이터 업로드
- 팀 전체 실사용
- 사내 정식 운영 배포
- 외부 URL 공유
- Public Streamlit 배포

## Known Backlog

- CloseCycle Excel cumulative columns 반영 확인/보완
- 최신 Excel 리포트 재생성
- Git 기준버전 미확보
- 실제 Streamlit 화면 캡처 보관

## U06.2 Candidate Follow-up

The CloseCycle Excel cumulative-column backlog was handled outside the frozen U06.1 ZIP as a U06.2 candidate patch.

- candidate_output: outputs/latest/daily_report_sales_20260610_v2.xlsx
- CloseCycle cumulative columns: CLOSED for the U06.2 candidate output
- latest Excel regeneration: CLOSED for the U06.2 candidate output
- old latest report snapshots without CloseCycle cumulative columns were moved to outputs/archive_old_format

## L4 Entry Conditions

- S1/S2 backlog closed 또는 승인된 waiver 존재
- 샘플/익명화 파일럿 피드백 정리
- 보안/권한 운영정책 확정
- 최신 Excel 산출물 검증
- pytest/Gate Runner ALL PASS

## Security Notes

- U06.1 L3 pilot remains sample/anonymized only.
- Real customer names, phone numbers, addresses, contract numbers, resident IDs, account numbers, and real customer identifiers are not allowed in pilot files.
- .streamlit/secrets.toml must not be printed, copied, or included in reports.
