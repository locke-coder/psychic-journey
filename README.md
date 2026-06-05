# sales-closing-forecast

## 공통 운영 원칙

이 문서는 `AGENTS.md`의 산식, 입력규칙, 보안규칙, 테스트규칙을 우선 적용합니다.

- 이 저장소는 입력주도형 영업 마감 예측툴입니다.
- 사용자가 영업일정, 마감일 여부, 일별 목표, 일별 누적 실적을 직접 입력합니다.
- 툴은 요일이나 날짜 패턴으로 마감일을 자동 추론하지 않습니다.
- 마감일 판단은 입력 파일의 `is_close_day` 컬럼만 기준으로 합니다.
- 입력표에 없는 날짜를 임의로 생성하지 않습니다.
- 기준일 이후 누적 실적은 비어 있을 수 있습니다.
- 일별 실적은 사용자가 입력하지 않고, 누적 실적의 차분으로 계산합니다.
- 원본 입력 파일은 절대 수정하지 않습니다.
- 고객명, 전화번호, 주소, 계약번호 등 개인정보 또는 민감정보는 저장하지 않습니다.
- 금액 단위는 기본적으로 억 원입니다.
- 금액 표시는 소수점 1자리, 달성률 표시는 `%` 소수점 1자리입니다.

## 프로젝트 목적

`sales-closing-forecast`는 사용자가 입력한 영업 일정과 누적 실적을 기준으로 월마감 예상 실적, 잔여 목표 상향 필요분, 다음 마감 필요실적을 계산하는 Streamlit 기반 도구입니다.

이 도구의 목적은 자동 날짜 추론이나 고객 단위 상세 분석이 아니라, 영업 운영자가 직접 관리하는 월간 입력표를 바탕으로 마감 리스크와 대응 시나리오를 빠르게 비교하는 것입니다.

## 주요 기능

- CSV 또는 XLSX 입력 파일 로딩
- 입력 파일 필수 컬럼, 기준일, 마감일, 목표, 누적 실적 검증
- `sales`와 `recognized` 지표 선택
- F1, F2, F3 예측모델 실행
- P1, P2, P3 프로비전 전략 실행
- F1/F2/F3와 P1/P2/P3의 3x3 시나리오 매트릭스 생성
- 다음 마감일과 다음 마감 필요실적 계산
- 위험등급 산정
- Excel 리포트 생성 및 다운로드

## 입력 파일 구조

입력 파일은 CSV 또는 XLSX 형식입니다. 날짜 행은 사용자가 직접 준비한 영업일정만 포함해야 하며, 툴은 누락된 날짜를 보완하거나 임의 생성하지 않습니다.

샘플 파일은 [data/sample/input_sample.csv](C:/Users/Owner/Documents/월 마감 실적 추정 TOOL/sales-closing-forecast/data/sample/input_sample.csv)에 있습니다.

## 필수 컬럼 설명

| 컬럼 | 설명 |
| --- | --- |
| `date` | 입력 행의 날짜입니다. 기준일은 반드시 이 컬럼에 존재해야 합니다. |
| `day_name` | 사용자가 입력한 요일명입니다. 표시용이며 마감일 자동 추론에 사용하지 않습니다. |
| `business_day_no` | 입력표 내 영업일 순번입니다. 중복 없이 오름차순이어야 합니다. |
| `is_close_day` | 마감일 여부입니다. `Y`, `YES`, `TRUE`, `1`, `True`는 마감일, `N`, `NO`, `FALSE`, `0`, 빈 값, `False`는 비마감일로 처리됩니다. |
| `close_type` | 마감 유형 메모입니다. 마감일인데 비어 있으면 warning으로 표시됩니다. |
| `sales_target_daily` | sales 기준 일별 목표입니다. |
| `recognized_target_daily` | recognized 기준 일별 목표입니다. |
| `sales_actual_cum` | sales 기준 누적 실적입니다. 기준일까지 입력되어야 하며 기준일 이후는 blank일 수 있습니다. |
| `recognized_actual_cum` | recognized 기준 누적 실적입니다. 기준일까지 입력되어야 하며 기준일 이후는 blank일 수 있습니다. |
| `memo` | 운영 메모입니다. 개인정보 또는 민감정보를 넣지 않습니다. |

월 목표는 기본적으로 선택 metric의 일별 목표 합계로 계산합니다. 일별 실적은 사용자가 입력하지 않으며, 누적 실적 차분으로 계산합니다.

```text
actual_daily_d = actual_cum_d - previous_actual_cum
```

## 예측모델 F1/F2/F3 설명

### F1: 누적 달성률 모델

기준일까지의 누적 실적을 기준일까지의 누적 목표로 나눈 누적 달성률을 잔여 모든 입력일에 적용합니다.

```text
r_cum = current_actual_cum / current_target_cum
forecast = current_actual_cum + remaining_target * r_cum
```

### F2: 직전 2개 완료 마감회차 모델

기준일 이하의 `is_close_day=True` 행 중 가장 최근 2개 완료 마감회차의 실적/목표 비율을 잔여 모든 입력일에 적용합니다. 완료 마감회차가 2개 미만이면 F1로 fallback합니다.

```text
r_last2 = sum(actual_daily of last two completed close cycles)
        / sum(target_daily of last two completed close cycles)
forecast = current_actual_cum + remaining_target * r_last2
```

### F3: 마감일/비마감일 가중 모델

기준일까지의 마감일과 비마감일을 분리해 각각의 달성률을 계산하고, 잔여 마감일에는 마감일 달성률을, 잔여 비마감일에는 비마감일 달성률을 적용합니다. 데이터가 부족하면 F2 또는 F1로 fallback합니다.

```text
forecast = current_actual_cum
         + sum(remaining close day target * r_close)
         + sum(remaining non-close day target * r_non_close)
```

## 프로비전 P1/P2/P3 설명

프로비전은 예측치가 월 목표에 부족할 때 잔여 목표를 얼마나 상향해야 하는지 계산하는 전략입니다.

- `P1_ALL_REMAINING`: 기준일 이후 모든 잔여 입력일에 일별 목표 비중대로 상향액을 배분합니다.
- `P2_CLOSE_DAY_FOCUSED`: 기준일 이후 `is_close_day=True`인 잔여 마감일에 우선 배분합니다.
- `P3_NON_CLOSE_DAY_FOCUSED`: 기준일 이후 `is_close_day=False`인 잔여 비마감일에 우선 배분합니다.

기본 cap rate는 마감일 1.30, 비마감일 1.50입니다. 수정 목표가 기존 목표와 cap rate의 곱을 초과하면 재배분을 시도하며, 재배분 후에도 부족하면 `CAPACITY_LIMITED`로 표시합니다.

## 설치 방법

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Streamlit 실행 방법

```bash
streamlit run app.py
```

앱은 제한 배포용 접속 비밀번호가 설정되어 있어야 열립니다. 로컬 실행 또는 배포 환경에 아래 둘 중 하나를 설정하세요.

```bash
set APP_ACCESS_PASSWORD=공유할_접속_비밀번호
streamlit run app.py
```

Streamlit Secrets를 쓰는 배포 환경에서는 `.streamlit/secrets.example.toml`의 값을 참고해 `APP_ACCESS_PASSWORD`를 등록합니다. 비밀번호를 평문으로 저장하지 않으려면 `APP_ACCESS_PASSWORD_SHA256`에 SHA-256 해시값을 등록할 수 있습니다.

브라우저에서 Streamlit 화면이 열리면 접속 비밀번호를 입력한 뒤 입력 파일을 업로드하거나 `샘플 데이터 로딩` 버튼으로 샘플 데이터를 사용할 수 있습니다.

## 샘플 데이터 실행 방법

샘플 데이터는 앱에서 자동으로 로딩할 수 있습니다.

1. `streamlit run app.py`를 실행합니다.
2. `샘플 데이터 로딩` 버튼을 누릅니다.
3. metric은 `sales` 또는 `recognized` 중 하나를 선택합니다.
4. 기준일은 입력표에 존재하고 해당 metric의 누적 실적이 입력된 날짜를 선택합니다.
5. `forecast model`과 `provision strategy`를 개별 선택하거나 `전체 비교`로 3x3 매트릭스를 확인합니다.

## Excel 리포트 생성 방법

Streamlit 앱의 `Excel 리포트 다운로드` 버튼을 누르면 계산 결과가 `.xlsx` 파일로 생성됩니다. 생성 파일은 `outputs` 폴더에도 저장됩니다.

Excel 리포트에는 다음 시트가 포함됩니다.

- `Summary`
- `ScenarioGrid`
- `DailyRevisedTargets`
- `CloseCycle`
- `Validation`
- `ReportText`

## 테스트 실행 방법

```bash
pytest -q
```

계산식을 변경하는 경우 반드시 관련 pytest 테스트를 추가하거나 수정해야 합니다. 테스트 실패가 있으면 코드를 무작정 고치기 전에 실패 원인을 먼저 확인합니다.

## 보안 주의사항

- 원본 입력 파일은 수정하지 않습니다.
- 실제 고객명, 전화번호, 주소, 상세 계약번호, 주민번호 등 개인정보 또는 민감정보를 입력 파일, 샘플 데이터, 로그, 문서, 리포트에 저장하지 않습니다.
- `memo`와 `close_type`에도 고객 식별 정보를 남기지 않습니다.
- 실데이터를 사용해야 하는 경우에도 익명화된 집계 값만 사용합니다.
- 결과물은 `outputs` 폴더에 생성되므로 공유 전 민감정보가 포함되지 않았는지 확인합니다.
