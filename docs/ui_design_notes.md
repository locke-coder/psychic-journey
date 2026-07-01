# U01-R Flat Pace Check UI Notes

## Concept

- 이름: 마감 페이스 체크
- 영문 보조: Month-End Pace Check
- 보조 문구: Daily Close Review
- 톤: 밝은 플랫 실무형
- 배경: 단색 웜 그레이
- 카드: 1px border 중심의 오프화이트 카드
- 강조색: muted teal 중심, amber/clay/green/blue는 상태 보조색으로만 사용

## Visual Guardrails

- 배경 그라데이션, 과한 그림자, 다크 관제형 표현은 사용하지 않는다.
- 외부 CDN, 외부 웹폰트, 외부 이미지는 추가하지 않는다.
- 전체 카드에 기본 그림자를 주지 않는다.
- 약한 강조 그림자는 아래 영역에만 허용한다.
  - `pace-mode-card`
  - `kpi-card.is-focus`
  - `scenario-card.is-emphasis`
  - `report-card.is-focus`
  - `download-card`

## Applied Structure

- Topbar: `MONTH-END PACE CHECK`, 기준월, 영업일차, 마감일 여부, 로컬 운영 배지.
- Hero: `Daily Close Review`, `마감 페이스 체크`, 오늘 기준 리포트/Excel 최신본/Backtest 확인 chip.
- 오늘의 운영모드: `target_status` 표시명과 설명을 표시한다.
- KPI 요약: 현재 누적 실적, 월마감 예상 실적, 월 목표, 목표 대비 차이, 목표 상태, 다음 마감 누적선 필요실적을 먼저 보여준다.
- 시나리오 체크: `scenario_df` 원본 row를 삭제하거나 추가하지 않고 카드형으로 표시한다.
- 보고 메모: `report_builder.py`가 만든 원문은 유지하고 화면에서만 카드 스타일을 적용한다.
- 예측 이력: history 파일이 없어도 깨지지 않는 기존 방어 로직을 유지한다.
- Excel 공유: `outputs/latest`의 최신 산출물만 기본 공유 대상으로 안내한다.

## Display Mapping

- `UNDER_TARGET`: 목표 보정 필요
- `ON_TARGET`: 유지/모니터링
- `OVER_TARGET`: 초과달성 관리
- `P1_ALL_REMAINING`: 전체 잔여 보정
- `P2_CLOSE_DAY_FOCUSED`: 마감일 집중
- `P3_NON_CLOSE_DAY_FOCUSED`: 비마감일 보정
- `O1_TARGET_HOLD_BUFFER`: 버퍼 유지
- `O2_STRETCH_TARGET_CAPTURE`: Stretch 전환
- `O3_QUALITY_GUARD_RELIEF`: 품질 방어
- Neutral/Maintain 계열: 유지/모니터링

## Logic Scope

- 이번 변경은 UI 롤백과 스킨 재적용만 포함한다.
- F1/F2/F3 산식, P1/P2/P3 보정, O1/O2/O3 초과달성 전략은 변경하지 않았다.
- `is_close_day` 기준을 유지하며 요일명이나 날짜 패턴으로 마감일을 추론하지 않는다.
- 원본 입력 파일, `secrets.toml`, config, 계산 모델, scenario runner, report builder, Excel exporter는 변경하지 않았다.
- 이전 다크 콘셉트는 사용자 화면에서 제거했다.
