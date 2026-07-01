# D06-A KPI · 예측 + 시나리오 통합

## 변경 전 문제

- `KPI · 예측` 화면과 `시나리오` 화면이 별도 메뉴로 노출되어 사용자가 운영 판단을 두 번 나누어 확인해야 했다.
- 두 화면 모두 `target_status`, `target_variance`, `surplus_to_target`, F1/F2/F3 모델 결과, 선택 시나리오, 권장 전략, O1/O2/O3 운영 전략을 반복해서 보여주었다.
- KPI 결론, 모델 비교, 운영전략 선택, 상세 검증표가 분산되어 월마감 판단 흐름이 끊겼다.

## 변경 후 구조

- canonical page key를 `forecast_strategy`로 통합했다.
- visible page title은 `예측 · 전략 통합`이다.
- 사이드바와 상단 네비게이션에는 통합 섹션 1개만 노출된다.
- 기존 `forecast`, `scenarios`, `scenario` query key는 `forecast_strategy`로 alias 처리된다.

## 정보 위계

1. 결론 요약
   - 목표 상태
   - 월마감 예상 실적
   - 목표 대비 차이
   - 초과 예상분
   - 다음 마감 누적선 필요실적
   - 운영모드
   - 권장 전략
   - 다음 액션

2. F1/F2/F3 모델 비교
   - 모델별 월말 예상 차이 중심으로 compact table을 표시한다.
   - 상세 KPI 반복을 피하기 위해 `surplus_to_target`, next close 상세값은 상단 요약 또는 expander에서만 확인한다.

3. 운영 판단판
   - 기존 `build_scenario_operation_matrix()`와 `_render_scenario_operation_matrix()`를 재사용한다.
   - ScenarioGrid 9개 row, P1/P2/P3, O1/O2/O3, N 계열 전략을 유지한다.
   - 추천 row 강조와 `strategy_label`, `strategy_group` 우선 표시를 유지한다.

4. 상세 분석 expander
   - `상세 차트와 잔여목표`: CloseCycle, 잔여 일자별 수정 목표, 전략 목표·버퍼·리스크 수준, 상세 차트 탭
   - `원본 ScenarioGrid`: 선택 시나리오 상세값과 전체 ScenarioGrid 원본
   - `과거 이력 / Backtest 참고`: historical context와 Backtest 참고 정보

## 호환성

- `?page=forecast`는 `forecast_strategy`로 열린다.
- `?page=scenarios`는 `forecast_strategy`로 열린다.
- `?page=scenario`도 `forecast_strategy`로 열린다.
- `render_forecast_page()`와 `render_scenarios_page()`는 compatibility wrapper로 유지하고, 실제 렌더링은 `render_forecast_strategy_page()`로 위임한다.

## 변경하지 않은 것

- F1/F2/F3 산식
- P1/P2/P3
- O1/O2/O3
- ScenarioGrid 9 row 원칙
- Excel exporter
- report builder
- forecast/provision/overachievement/scenario 계산 로직
- `is_close_day` 기준 마감일 판정 규칙

## QA 체크리스트

- 통합 페이지 `예측 · 전략 통합` 표시
- `forecast`, `scenarios` query alias가 fallback home이 아니라 통합 페이지로 normalize
- 선택 시나리오 변경 시 요약, 판단판, 상세표가 함께 갱신
- O1/O2/O3 라벨이 `버퍼 유지`, `Stretch 전환`, `품질 방어`로 구분
- P1/P2/P3 라벨이 유지
- raw ScenarioGrid expander에서 전체 원본 확인 가능
- 관련 pytest PASS
- full pytest PASS
- Gate Runner ALL PASS
- forbidden pattern scan 0건
