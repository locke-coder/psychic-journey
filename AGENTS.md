# AGENTS.md

이 저장소에서 작업하는 에이전트는 아래 산식, 입력규칙, 보안규칙, 테스트규칙을 우선 적용한다. 계산식을 변경하는 경우 반드시 관련 pytest 테스트를 추가하거나 수정하고, 각 단계 완료 후 `pytest -q`를 실행해 결과를 보고한다.

## Business Context

- 이 프로젝트는 입력주도형 영업 마감 예측툴이다.
- 사용자가 영업일정, 마감일 여부, 일별 목표, 일별 누적 실적을 직접 입력한다.
- 툴은 입력값을 검증하고, 월마감 예상실적과 잔여 목표 상향안을 계산한다.
- 주요 지표는 sales와 recognized다.
- 기본 금액 단위는 억 원이다.

## Required Input Columns

입력 파일에는 아래 컬럼이 필요하다.

```text
date
day_name
business_day_no
is_close_day
close_type
sales_target_daily
recognized_target_daily
sales_actual_cum
recognized_actual_cum
memo
```

## Core Input Rules

1. 마감일은 `is_close_day` 컬럼으로만 판단한다.
2. 요일로 마감일을 자동 추론하지 않는다.
3. 입력표에 없는 날짜를 임의로 생성하지 않는다.
4. 기준일 이후 누적 실적은 blank일 수 있다.
5. 기준일 이전 또는 기준일까지의 누적 실적은 계산을 위해 필요하다.
6. 월 목표는 기본적으로 일별 목표 합계로 계산한다.
7. 일별 목표 누적은 툴이 자동 계산한다.
8. 일별 실적은 누적 실적 차분으로 계산한다.

## Actual Daily Calculation

사용자는 누적 실적만 입력한다.
툴은 일별 실적을 아래 공식으로 계산한다.

```text
actual_daily_d = actual_cum_d - previous_actual_cum
```

첫 번째 입력일의 `actual_daily`는 `actual_cum`과 동일하다.
누적 실적이 감소하면 warning으로 표시한다.
단, 취소/조정 반영 가능성이 있으므로 config에서 `allow_negative_daily_actual` 옵션을 둘 수 있다.

## Forecast Models

### F1: Cumulative Achievement Rate

```text
current_target_cum = sum(target_daily where date <= as_of_date)
current_actual_cum = actual_cum at as_of_date
remaining_target = sum(target_daily where date > as_of_date)

r_cum = current_actual_cum / current_target_cum
forecast = current_actual_cum + remaining_target * r_cum
```

잔여일 `expected_rate_by_day`는 모두 `r_cum`이다.

### F2: Last Two Completed Close Cycles

직전 2개 완료 마감일은 기준일 이하의 `is_close_day=True` 행 중 가장 최근 2개다.
마감회차는 직전 마감일 다음 행부터 해당 마감일 행까지다.
첫 마감회차는 입력표 첫 행부터 첫 마감일 행까지다.

```text
r_last2 =
sum(actual_daily of last two completed close cycles)
/ sum(target_daily of last two completed close cycles)

forecast = current_actual_cum + remaining_target * r_last2
```

완료 마감회차가 2개 미만이면 F1로 fallback한다.

### F3: Daily and Close Day Weighted Model

마감일은 `is_close_day=True` 행이다.
비마감일은 `is_close_day=False` 행이다.

```text
r_close =
sum(actual_daily where date <= as_of_date and is_close_day=True)
/ sum(target_daily where date <= as_of_date and is_close_day=True)

r_non_close =
sum(actual_daily where date <= as_of_date and is_close_day=False)
/ sum(target_daily where date <= as_of_date and is_close_day=False)

forecast =
current_actual_cum
+ sum(remaining close day target * r_close)
+ sum(remaining non-close day target * r_non_close)
```

잔여 마감일 `expected_rate_by_day`는 `r_close`다.
잔여 비마감일 `expected_rate_by_day`는 `r_non_close`다.

데이터 부족 시 F2 또는 F1로 fallback한다.

## Provision Models

### P1: All Remaining Allocation

기준일 이후 모든 잔여일에 `target_daily` 비중대로 상향액을 배분한다.

### P2: Close Day Focused Allocation

기준일 이후 `is_close_day=True`인 잔여 마감일에만 우선 배분한다.
마감일 대상이 없으면 `NOT_APPLICABLE` 또는 fallback 규칙을 따른다.

### P3: Non-Close Day Focused Allocation

기준일 이후 `is_close_day=False`인 잔여 비마감일에만 우선 배분한다.
비마감일 대상이 없으면 `NOT_APPLICABLE` 또는 fallback 규칙을 따른다.

## Provision Formula

```text
base_forecast = current_actual_cum + sum(remaining_target_d * expected_rate_d)
gap = max(0, monthly_target - base_forecast)
uplift_effective_rate = sum(allocation_weight_d * expected_rate_d)
required_uplift = gap / uplift_effective_rate
revised_target_d = original_target_d + required_uplift * allocation_weight_d
```

`gap`이 0이면 `required_uplift`는 0이다.
`uplift_effective_rate`가 0이면 계산 불가로 처리한다.

## Cap Rules

`close_day_cap_rate` 기본값은 1.30이다.
`non_close_day_cap_rate` 기본값은 1.50이다.

수정 목표가 기존 목표 * `cap_rate`를 초과하면 초과분을 재배분한다.
재배분 불가 시 `status = CAPACITY_LIMITED`로 표시한다.
`CAPACITY_LIMITED`일 때 목표 달성이 가능한 것처럼 표시하지 않는다.

## Output Rules

- 금액은 억 원 기준 소수점 1자리로 표시한다.
- 달성률은 % 기준 소수점 1자리로 표시한다.
- 원본 입력 파일은 수정하지 않는다.
- `outputs` 폴더에 결과물을 생성한다.

## Security

- 실제 고객명, 전화번호, 주소, 상세 계약번호, 주민번호 등 PII는 저장하지 않는다.
- 개발용 샘플 데이터는 익명화한다.
- 실데이터가 필요한 경우에도 원본 파일을 수정하지 않는다.

## Testing Rules

- 산식 변경 시 pytest 테스트가 있어야 한다.
- `forecast_models.py`, `provision_models.py`, `scenario_runner.py` 변경 후에는 반드시 `pytest -q`를 실행한다.
- 테스트 실패 시 실패 원인을 먼저 설명하고 수정한다.
