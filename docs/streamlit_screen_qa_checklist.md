# Streamlit Screen QA Checklist - L4 Release Candidate

## Scope

이 체크리스트는 L4 사내 정식 운영 후보 승인 전 Streamlit 화면을 수동 점검하기 위한 기준이다.
실제 private 영업 데이터는 Public Streamlit URL에 업로드하지 않는다.

## Evidence Status

- Local Streamlit smoke: PASS, HTTP 200 확인
- Local URL used for smoke: http://127.0.0.1:8501
- Full visual screen QA: manual required
- External Streamlit URL QA: manual required
- Private operating data upload to public URL: prohibited

## 1. Home / 마감 페이스 체크

- [ ] 월마감 상태판이 표시된다.
- [ ] 기준월이 표시된다.
- [ ] 목표 상태가 표시된다.
- [ ] 월마감 예상 실적이 표시된다.
- [ ] 목표 대비 차이가 표시된다.
- [ ] 다음 마감 누적선 필요실적이 표시된다.
- [ ] 운영모드가 표시된다.
- [ ] 추천 전략이 표시된다.
- [ ] 보안 경고가 표시된다.

## 2. KPI / 예측

- [ ] F1/F2/F3 모델 비교가 표시된다.
- [ ] target_status가 표시된다.
- [ ] target_variance가 표시된다.
- [ ] surplus_to_target이 표시된다.
- [ ] 과거 중앙값/밴드가 표시된다.
- [ ] 과거 데이터가 없으면 안전 안내가 표시된다.
- [ ] 차트가 깨짐 없이 렌더링된다.

## 3. 시나리오

- [ ] ScenarioGrid가 9개 row로 표시된다.
- [ ] P1_ALL_REMAINING이 유지된다.
- [ ] P2_CLOSE_DAY_FOCUSED가 유지된다.
- [ ] P3_NON_CLOSE_DAY_FOCUSED가 유지된다.
- [ ] O1_TARGET_HOLD_BUFFER가 유지된다.
- [ ] O2_STRETCH_TARGET_CAPTURE가 유지된다.
- [ ] O3_QUALITY_GUARD_RELIEF가 유지된다.
- [ ] O1 전략 라벨이 "버퍼 유지"로 구분된다.
- [ ] O2 전략 라벨이 "Stretch 전환"으로 구분된다.
- [ ] O3 전략 라벨이 "품질 방어"로 구분된다.
- [ ] 추천 row가 강조된다.
- [ ] raw technical data expander가 존재한다.

## 4. 보고 메모

- [ ] 중복 종결어미가 없다.
- [ ] OVER_TARGET 상태에서 "목표 초과 예상" 문구가 유지된다.
- [ ] 취소/철회/미결제 리스크 문구가 유지된다.
- [ ] 다음 액션이 표시된다.

## 5. 예측 이력 / Backtest

- [ ] ForecastHistory가 표시된다.
- [ ] FinalActuals가 표시되거나, 데이터가 없으면 안전 안내가 표시된다.
- [ ] BacktestSummary가 표시된다.
- [ ] ModelWeights가 표시된다.
- [ ] ConfidenceBand가 표시된다.
- [ ] Insights가 표시된다.
- [ ] history missing 상태가 안전하게 처리된다.

## 6. Excel 공유

- [ ] latest Excel 파일이 표시된다.
- [ ] freshness badge가 표시된다.
- [ ] download button이 동작한다.
- [ ] ScenarioGrid 최신 컬럼 점검 안내가 표시된다.
- [ ] archive_invalid가 화면에 노출되지 않는다.

## Result Form

- QA date:
- QA owner:
- Environment:
- Dataset type: sample / anonymized / private-local
- Overall result: PASS / FAIL / BLOCKED
- Failed items:
- Evidence path:
- Notes without private values:

