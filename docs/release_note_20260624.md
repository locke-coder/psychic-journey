# Release Note 2026-06-24

## 1. Release Summary

- release_name: `sales_closing_forecast_l4_candidate_20260624`
- release_status: `L4_READY_PACKAGE_ONLY`
- release_commit: `70139e39c25f12749c92b8906266dac8a26e8c89`
- app_url: `https://locke-coder-psychic-journey-app-cxfzqk.streamlit.app/`
- audit_package: `audit_submit.zip`
- release_date: `2026-06-24`

이번 릴리즈는 운영 인수 가능한 감사 패키지와 문서 세트를 제공하는 상태다. R07 기준 최종 결과는 `CONDITIONAL_PASS`이며, 원격 Streamlit 반영 상태와 실데이터 운영 접근 통제는 별도 승인 확인이 필요하다.

## 2. 주요 기능

- 사용자가 입력한 영업일정, 마감일 여부, 일별 목표, 일별 누적 실적 기반 월마감 예상실적 계산
- `is_close_day` 컬럼만을 기준으로 한 마감일 판단
- F1/F2/F3 Forecast 모델 제공
- P1/P2/P3 목표 미달 보정전략 제공
- O1/O2/O3 초과달성 운영전략 제공
- 목표 미달, 근접, 초과 상태와 목표 차이 표시
- History/Backtest 화면을 통한 예측 흐름 점검
- 보고문 생성 및 Excel 리포트 생성
- `target_status`, `target_variance`, `surplus_to_target`, `recommended_action` 등 운영 판단 컬럼 제공

## 3. 검증 결과

- pytest: `PASS`, `357 passed`
- G23_OUTPUTS_LATEST_STRICT: `PASS`
- Gate Runner ALL: `PASS`
- R04 GitHub main push/post-verify: 완료
- R05 Streamlit smoke: 완료, remote auth redirect로 Cloud UI/deploy-status reflection은 사용자 수동 확인 필요
- R06 Excel 최신 산출물 검증: `PASS`
- R06.1 OverTarget Excel 산출물 검증: `PASS`
- R07 최종 운영 승인 패키지: `CONDITIONAL_PASS`
- audit package validation: `audit_submit.zip` 검증 완료
- secrets, env, key, archive_invalid 제외 확인
- 실데이터 업로드 없음
- secrets 조회 없음

## 4. Excel 산출물

검증된 Excel 산출물 기준은 아래와 같다.

- latest sample workbook: `outputs/latest/daily_report_sales_20260610_v2.xlsx`
- over-target workbook: `outputs/latest/daily_report_sales_20260610_over_target_v1.xlsx`
- required sheets: `Summary`, `ScenarioGrid`, `DailyRevisedTargets`, `CloseCycle`, `Validation`, `ReportText`
- optional history/backtest sheets: `ForecastHistory`, `BacktestSummary`, `ModelWeights`, `ConfidenceBand`, `Insights`
- key columns: `target_status`, `target_variance`, `surplus_to_target`, `strategy_type`, `overachievement_strategy`, `recommended_action`
- over-target strategies confirmed: `O1_TARGET_HOLD_BUFFER`, `O2_STRETCH_TARGET_CAPTURE`, `O3_QUALITY_GUARD_RELIEF`

## 5. 알려진 Caveat

- 원격 Streamlit 앱 URL은 Streamlit auth redirect가 있어 Codex에서 내부 UI, Cloud deploy status, reflected commit을 직접 검증하지 못했다.
- Streamlit Cloud 상태, 마지막 배포 성공 여부, source branch `main`, 반영 commit은 운영자 브라우저에서 수동 확인해야 한다.
- R06.1 OverTarget Excel 산출물은 `audit_submit.zip`에 포함되어 있으나, 원격 앱에 해당 산출물 상태를 반영하려면 별도 승인된 push/redeploy 흐름이 필요하다.
- Workspace root에는 Git metadata가 없으며, 배포 traceability는 deploy source repository와 R05/R07 증빙을 기준으로 한다.
- Public URL에는 실데이터를 업로드하지 않는다.

## 6. 운영 제한사항

- 코드, 테스트, 설정, 샘플 데이터, outputs, `audit_submit.zip` 변경 없이 문서 인수 단계로 종료한다.
- GitHub push와 Streamlit redeploy는 R08 범위에 포함하지 않는다.
- 실데이터 사용 전 Private 배포 또는 승인된 접근 통제가 필요하다.
- 마감일 판단은 `is_close_day` 컬럼만 사용한다.
- `day_name`은 표시용으로만 사용한다.
- F1/F2/F3 산식, P1/P2/P3 미달 시나리오, O1/O2/O3 초과달성 시나리오는 임의로 변경하거나 삭제하지 않는다.
- `.streamlit/secrets.toml`의 실제 내용은 읽거나 출력하거나 복사하지 않는다.

## 7. 다음 고도화 후보

- Private 배포 및 접근 권한 운영 절차 확정
- Streamlit Cloud UI에서 반영 commit, 배포 성공 상태, 접근 권한을 수동 캡처하여 보관
- 실데이터 업로드 전 데이터 승인 양식과 익명화 체크리스트 확정
- 운영자 교육용 샘플 시나리오 정리
- Excel 공유 승인 흐름과 파일 보관 정책 정리
- L4_READY 전환을 위한 별도 승인 push/redeploy 및 post-deploy verification 절차 수행
