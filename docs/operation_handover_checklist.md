# R08 Operation Handover Checklist

## 1. Release Identity

- release_name: `sales_closing_forecast_l4_candidate_20260624`
- release_status: `L4_READY_PACKAGE_ONLY`
- release_commit: `70139e39c25f12749c92b8906266dac8a26e8c89`
- app_url: `https://locke-coder-psychic-journey-app-cxfzqk.streamlit.app/`
- audit_package: `audit_submit.zip`
- handover_date: `2026-06-24`

## 2. Approval Checklist Before Operation

운영 인수 전 승인자는 아래 항목을 확인한다.

- [ ] 릴리즈 commit이 `70139e39c25f12749c92b8906266dac8a26e8c89`인지 확인한다.
- [ ] `audit_submit.zip` 제출본이 R07 최종 검증 패키지인지 확인한다.
- [ ] pytest `357 passed`, `G23_OUTPUTS_LATEST_STRICT: PASS`, `Gate Runner ALL: PASS` 결과를 확인한다.
- [ ] R06.1 OverTarget Excel 산출물이 `audit_submit.zip`에 포함되어 있음을 확인한다.
- [ ] Streamlit Cloud 상태, 마지막 배포 성공 여부, source branch `main`, 반영 commit은 운영자 브라우저에서 수동 확인한다.
- [ ] Public URL에서 실데이터를 사용하지 않는다는 제한을 운영자와 승인자가 공동 확인한다.
- [ ] 실데이터 운영이 필요하면 Private 배포 또는 승인된 내부 접근 제한을 먼저 적용한다.

## 3. Operating Data Restrictions

- Public URL에는 샘플 또는 익명화 데이터만 입력한다.
- 실제 고객명, 전화번호, 주소, 계약번호, 주민번호, 원장 식별자 등 민감정보를 입력 파일, 메모, 보고문, Excel 산출물에 포함하지 않는다.
- 운영 원본 파일은 수정하지 않는다. 필요한 경우 승인된 별도 복사본으로 작업한다.
- 마감일은 입력 컬럼 `is_close_day` 값으로만 판단한다. 요일, 날짜 패턴, `day_name`으로 마감일을 추론하지 않는다.
- `day_name`은 표시용으로만 사용한다.

## 4. Public URL Restrictions

- 현재 app URL은 운영 승인 전까지 broad public 운영 채널로 사용하지 않는다.
- Public URL에서는 실제 영업자료, 미공개 실적, 고객 또는 계약 식별 정보가 포함된 파일 업로드를 금지한다.
- Public URL 접근 권한, 비밀번호 게이트, 접속 로그 정책은 운영자가 별도 승인 기록으로 보관한다.

## 5. Private Deployment Recommendation

실데이터 사용 전 아래 조건을 충족하는 Private 배포를 권장한다.

- 승인된 사용자만 접근 가능한 배포 방식
- 접근 권한 변경 이력 관리
- 운영 데이터 업로드 승인 절차
- 민감정보 제거 또는 익명화 기준
- 배포 commit과 감사 패키지 commit의 대응 관계 확인
- Streamlit Cloud 또는 내부 배포 환경에서 배포 상태와 반영 commit 확인

## 6. Required Approvals Before Real Data Upload

실데이터 업로드 전 아래 승인이 필요하다.

- [ ] 데이터 소유 부서 승인
- [ ] 보안 또는 개인정보 책임자 승인
- [ ] 운영 책임자 승인
- [ ] 접근 권한 승인
- [ ] 입력 파일의 민감정보 제거 확인
- [ ] `memo` 컬럼에 개인 또는 계약 식별 정보가 없음을 확인
- [ ] 결과 보고문과 Excel 산출물의 공유 범위 승인

## 7. Excel Report Sharing Criteria

Excel 산출물 공유 전 아래 기준을 적용한다.

- `Summary`, `ScenarioGrid`, `DailyRevisedTargets`, `CloseCycle`, `Validation`, `ReportText` 시트가 포함되어야 한다.
- `target_status`, `target_variance`, `surplus_to_target`, `strategy_type`, `overachievement_strategy`, `recommended_action` 컬럼을 확인한다.
- P1/P2/P3 미달 보정 시나리오와 O1/O2/O3 초과달성 운영 시나리오가 정책상 삭제되지 않았는지 확인한다.
- 산출물에 민감정보가 없음을 확인한 뒤 승인된 대상에게만 공유한다.
- Public URL 또는 외부 채널에 실데이터 기반 Excel 파일을 공유하지 않는다.

## 8. Incident Check Items

장애 또는 이상 결과 발생 시 아래 항목을 우선 확인한다.

- 기준월, 기준일 선택이 입력 데이터 범위와 맞는지 확인한다.
- 기준일까지의 누적 실적이 비어 있지 않은지 확인한다.
- 기준일 이후 누적 실적 blank 허용 범위가 맞는지 확인한다.
- `is_close_day` 입력값이 마감일 정책과 일치하는지 확인한다.
- 일별 목표 합계가 월 목표 기준과 맞는지 확인한다.
- 누적 실적 감소 warning이 취소 또는 조정 반영인지 확인한다.
- Forecast, Scenario, History/Backtest, Excel Export 화면이 동일 기준월과 기준일을 보고 있는지 확인한다.
- Excel 재생성 시 샘플 또는 승인된 익명 데이터만 사용했는지 확인한다.

## 9. Rollback Or Hotfix Entry Criteria

Rollback 또는 hotfix는 아래 조건 중 하나 이상이 확인될 때 진입한다.

- `is_close_day`가 아닌 요일 또는 날짜 패턴으로 마감일이 판단되는 회귀가 확인됨
- F1/F2/F3 산식 결과가 승인된 기대값과 다름
- P1/P2/P3 미달 시나리오가 누락되거나 잘못 단순화됨
- O1/O2/O3 초과달성 시나리오가 누락되거나 `NO_GAP`으로 대체됨
- Excel 필수 시트 또는 필수 컬럼이 누락됨
- Public URL에서 실데이터 업로드 또는 민감정보 노출이 확인됨
- 배포 commit이 승인 commit과 다르거나 배포 상태가 실패로 확인됨
- 승인되지 않은 코드, 테스트, 설정, 샘플, outputs 변경이 확인됨

Rollback 또는 hotfix 진입 시에는 추가 입력을 중단하고, 감사 패키지와 운영 로그를 보존한 뒤 별도 승인된 수정 절차로 이동한다.
