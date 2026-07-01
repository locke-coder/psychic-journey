# L4 Operation Protocol: U06.2

## 1. Purpose

U06.2 승인본 기준 사내/Private 운영 절차를 정의한다.

## 2. Operation Scope

- 승인된 내부 사용자만 사용한다.
- 승인된 데이터만 사용한다.
- 외부 공유를 금지한다.
- Public URL 노출을 금지한다.

## 3. Data Policy

- 샘플/익명화 데이터를 우선 사용한다.
- 실데이터 사용 시 내부 승인을 먼저 확보한다.
- 고객명, 전화번호, 주민번호, 주소, 계좌번호, 계약번호 등 직접식별자를 제거한다.
- 파일 업로드 전 민감정보 포함 여부를 점검한다.
- 원본 운영 입력 파일은 수정하지 않는다.

## 4. Operation Procedure

1. 승인 ZIP SHA256을 확인한다.
2. venv를 준비한다.
3. requirements를 설치한다.
4. pytest와 Gate Runner 결과를 확인한다.
5. Streamlit을 실행한다.
6. 샘플 입력으로 계산 결과를 검증한다.
7. Excel 다운로드를 검증한다.
8. 실행 결과와 증빙을 기록한다.

## 5. File Management

- outputs/latest만 공유 가능하다.
- outputs/archive_invalid 공유를 금지한다.
- outputs/archive_old_format 공유를 금지한다.
- .streamlit/secrets.toml 공유를 금지한다.
- .streamlit/secrets.example.toml은 예시 파일로만 사용한다.

## 6. Stop Criteria

- S1 발견
- SHA 불일치
- 민감정보 노출
- 계산 결과 명백 오류
- Public URL 노출

## 7. Feedback Severity

| severity | meaning | operation rule |
|---|---|---|
| S1 | 즉시 운영 중단 필요 | 운영 중단 후 승인자 확인 |
| S2 | 운영 전 또는 다음 릴리즈 전 필수 처리 | 처리 계획과 담당자 지정 |
| S3 | 운영 가능하나 개선 필요 | register에 기록 후 추적 |
| S4 | 선택 개선 | backlog 후보로 관리 |

## 8. Core Input Controls

- 마감일 판단은 is_close_day 컬럼만 사용한다.
- day_name은 표시용으로만 사용한다.
- 입력표에 없는 날짜를 임의로 생성하지 않는다.
- target / actual 입력 컬럼을 운영 전 확인한다.
