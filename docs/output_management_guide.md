# outputs 관리 가이드

## 폴더 의미

`outputs/latest/`는 현재 공유 가능한 최신 포맷 산출물 위치다. 최신 리포트 워크북과 정상 입력 템플릿처럼 운영 공유 대상으로 삼을 수 있는 파일만 둔다.

`outputs/archive_old_format/`는 열리지만 최신 필수 시트가 부족한 구버전 포맷 산출물 위치다. 보존 목적이며 기본 감리 패키지에는 포함하지 않는다.

`outputs/archive_invalid/`는 `openpyxl`로 열리지 않는 invalid xlsx 격리 위치다. 파일은 삭제하지 않고 보존하되 운영 공유 대상으로 사용하지 않는다.

## manage_outputs.py 사용법

현재 분류 상태를 확인한다.

```powershell
.\.venv\Scripts\python.exe tools\manage_outputs.py scan
```

이동 예정 결과만 확인한다.

```powershell
.\.venv\Scripts\python.exe tools\manage_outputs.py organize --dry-run
```

실제 정리를 실행한다.

```powershell
.\.venv\Scripts\python.exe tools\manage_outputs.py organize
```

Markdown 형태의 보고서를 출력한다.

```powershell
.\.venv\Scripts\python.exe tools\manage_outputs.py report
```

## invalid xlsx 처리

Excel 파일을 `openpyxl.load_workbook`으로 열 수 없으면 `invalid`로 분류하고 `outputs/archive_invalid/`로 이동한다. invalid 파일은 삭제하지 않는다. 입력 템플릿이 invalid로 격리되면 `outputs/latest/month_close_forecast_input_template.xlsx`에 정상 템플릿을 새로 생성한다.

## 최신 포맷 판정

리포트 워크북은 `Summary`, `ScenarioGrid`, `DailyRevisedTargets`, `CloseCycle`, `Validation`, `ReportText` 시트가 모두 있으면 latest로 분류한다. `ForecastHistory`, `FinalActuals`, `BacktestSummary`, `ModelWeights`, `ConfidenceBand`, `Insights` 시트가 있으면 최신 고도화 산출물로 볼 수 있다.

D03 이후 `ScenarioGrid`는 계산용 원본 컬럼과 표시/공유용 컬럼을 함께 가진다. 최신 공유본의 필수 표시 컬럼은 `scenario`, `forecast_model`, `model_name`, `expected_month_end_amount`, `target_status`, `target_variance`, `surplus_to_target`, `strategy_type`, `strategy_code`, `overachievement_strategy`, `strategy_label`, `strategy_group`, `stretch_uplift`, `revised_monthly_target`, `remaining_surplus_buffer`, `minimum_remaining_to_hit_target`, `relief_amount`, `recommended_action`, `risk_note`이다.

단, D02 정리 기준에서 구버전 산출물로 식별된 `daily_report_*_20260602.xlsx`, `daily_report_sales_20260604.xlsx`는 보존용 old_format으로 분류한다.

입력 템플릿은 `date`, `day_name`, `business_day_no`, `is_close_day`, `close_type`, `sales_target_daily`, `recognized_target_daily`, `sales_actual_cum`, `recognized_actual_cum`, `memo` 헤더가 있으면 latest로 분류한다. `day_name`은 표시용이며 마감일 판정에는 사용하지 않는다.

## 운영 공유 원칙

운영 공유와 감리 제출에는 `outputs/latest/`의 최신 산출물만 사용한다. `archive_old_format`과 `archive_invalid`는 보존과 원인 추적용이며 기본 공유 대상이 아니다.

Public Streamlit 또는 외부 공개 URL에는 실제 영업실적을 업로드하지 않는다. 실데이터는 Private/사내망/권한 통제 환경에서만 사용한다. `.streamlit/secrets.toml`, `.env`, `*.key`, `*secret*`, `*secrets*` 파일은 감리 제출 패키지와 운영 공유 산출물에 포함하지 않는다.
