# L4 Release Runbook

## 1. 릴리즈 목적

입력주도형 월마감 영업실적 예측툴을 L4 사내 정식 운영 후보로 제출하기 전, 테스트, Gate, Excel, Streamlit smoke, 보안 패키징 증빙을 재생성한다.

## 2. 실행 환경

- OS: Windows / PowerShell
- Python: .venv 내 Python 사용
- 실행 위치: 저장소 루트
- 실제 private 영업 데이터는 저장소와 audit package에 포함하지 않는다.

## 3. 필수 명령

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe tools\gate_runner.py ALL
.\.venv\Scripts\python.exe tools\collect_audit_artifacts.py
```

## 4. 테스트 명령

```powershell
.\.venv\Scripts\python.exe -m pytest -q 2>&1 | Tee-Object -FilePath audit\logs\l4_final_pytest.txt
```

성공 기준:

- return code 0
- 실제 passed count 기록
- 테스트 삭제, skip, 기대값 완화 없음

## 5. Gate 명령

```powershell
.\.venv\Scripts\python.exe tools\gate_runner.py ALL > audit\logs\l4_gate_runner_all.json
```

성공 기준:

- status: PASS
- forbidden_patterns_found: []
- source forbidden pattern 0

## 6. Streamlit 실행 명령

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.headless true --server.port 8501
```

Smoke 확인:

```powershell
Invoke-WebRequest -Uri "http://127.0.0.1:8501" -UseBasicParsing
```

성공 기준:

- HTTP 200
- 화면 전체 QA는 docs/streamlit_screen_qa_checklist.md 기준으로 수동 확인
- Public Streamlit URL에 private 데이터를 업로드하지 않음

## 7. Excel 검증 명령

대상 파일:

```text
outputs/latest/daily_report_sales_20260610_v2.xlsx
```

검증 기준:

- openpyxl load PASS
- ScenarioGrid 존재
- ScenarioGrid row count 9
- 최신 ScenarioGrid 필수 컬럼 모두 존재
- ForecastHistory, FinalActuals, BacktestSummary, ModelWeights, ConfidenceBand, Insights 시트 존재

## 8. 감리 패키지 생성 명령

```powershell
.\.venv\Scripts\python.exe tools\collect_audit_artifacts.py
```

확인 기준:

- audit_submit.zip 생성
- manifest.md 포함
- audit/logs/l4_* 로그 포함
- docs/l4_release_runbook.md 포함
- docs/private_data_qa_guide.md 포함
- docs/streamlit_screen_qa_checklist.md 포함
- outputs/latest 포함
- outputs/archive_invalid 미포함
- outputs/archive_old_format 기본 미포함
- .streamlit/secrets.toml, .env, *.key 미포함

## 9. Rollback 절차

1. 현재 운영 승인 요청을 보류한다.
2. FAIL 또는 BLOCKED 로그를 audit/l4_release_readiness.md에 남긴다.
3. 기능 파일은 즉시 수정하지 않는다.
4. 결함 분류 후 별도 패치 티켓에서 원인 분석과 수정 범위를 승인받는다.
5. 수정 후 D04 전체 절차를 처음부터 재실행한다.

## 10. 장애 대응

- Python 실행 불가: BLOCKED로 기록하고 환경 복구 후 재시도한다.
- pytest 실패: FAIL로 기록하고 테스트명과 원인을 보고한다.
- Gate 실패: FAIL로 기록하고 금지 패턴 또는 누락 파일을 보고한다.
- Excel load 실패: BLOCKED 또는 FAIL로 기록하고 파일 존재 여부와 오류 유형을 남긴다.
- Streamlit 실행 불가: 환경 제약과 오류 메시지를 기록하고 manual required로 격상한다.
- audit package 생성 불가: BLOCKED로 기록한다.

## 11. 보안 주의

- .streamlit/secrets.toml 내용을 읽거나 출력하지 않는다.
- 실제 고객명, 전화번호, 주소, 계약번호, 주민번호를 문서, 테스트, 샘플, 로그에 기록하지 않는다.
- Public Streamlit URL에 실제 운영 데이터를 업로드하지 않는다.
- audit_submit.zip에 private 데이터 원본이나 private output을 포함하지 않는다.
- archive_invalid와 archive_old_format은 기본 제외 상태를 유지한다.

## 12. 운영 승인 체크리스트

- [ ] pytest PASS
- [ ] Gate Runner ALL PASS
- [ ] source forbidden pattern 0
- [ ] latest Excel openpyxl load PASS
- [ ] ScenarioGrid 최신 컬럼 PASS
- [ ] Streamlit local smoke PASS
- [ ] screen QA PASS
- [ ] private data QA PASS
- [ ] secrets/env/key 미포함
- [ ] archive_invalid 미포함
- [ ] archive_old_format 기본 미포함
- [ ] 배포 버전 기록

