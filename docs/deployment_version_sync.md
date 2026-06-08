# 배포/로컬 버전 동기화 기록

## 동기화 기준

- 배포 앱: https://share.streamlit.io/locke-coder/psychic-journey/main/app.py
- 원격 배포 저장소: `locke-coder/psychic-journey`
- 원격 배포 브랜치: `main`
- 로컬 배포 폴더: `outputs/streamlit_deploy_source`

운영 기준은 원격 `main`과 로컬 배포 폴더의 Git HEAD가 같은 상태인지로 판단한다.
기능 변경을 배포할 때는 원본 작업 파일에 반영한 뒤 로컬 배포 폴더에도 같은 변경을 반영하고,
테스트와 문법 확인 후 원격 `main`에 푸시한다.

## 최근 확인

- 확인일: 2026-06-08 KST
- 확인 결과: `MATCH`
- 원격 `main` 기준 앱 내용 커밋: `07571e4367d976b900602948e68e38d7908a24dc`
- 로컬 배포 폴더 앱 내용 기준 커밋: `07571e4367d976b900602948e68e38d7908a24dc`
- GitHub compare 결과: `07571e4367d976b900602948e68e38d7908a24dc` vs `main` = `identical`
- 이 문서 자체를 기록/갱신하는 커밋 때문에 Git HEAD는 앱 내용 기준 커밋보다 앞설 수 있다.

## 배포 주요 파일 해시

| 파일 | Git blob | SHA-256 prefix |
| --- | --- | --- |
| `app.py` | `36874cddfe56ac0e77eaaa45fe01d9478b19d52a` | `55E3EBEB6C2E5886` |
| `data/sample/input_sample.csv` | `8d20123c4ad77e4a7d382c19e36cea5b34c029f3` | `5DA279DA2FBD` |
| `data/sample/historical_input_sample.csv` | `74fe3923dd3088f82a12b9bdb1948dfc1ba75348` | `FF7F6201001840D1` |
| `outputs/latest/month_close_forecast_input_template.xlsx` | `e0422bbcd9b62fd19ffe1cc009b94943a759b534` | `9F2DF6D25051` |
| `outputs/latest/historical_month_close_forecast_input_template.xlsx` | `6dc4388791d4e483088ebf9adc1d8be3e409137a` | `DEC01CCF421BDDAC` |

## 현재 주의사항

- 로컬 배포 폴더에는 미배포 변경 `src/excel_exporter.py`가 남아 있다. 이 파일은 현재 원격 `main`에 반영된 배포 버전으로 보지 않는다.
- 원본 작업 폴더와 로컬 배포 폴더를 비교하면 `app.py`, `data/sample/historical_input_sample.csv`, `outputs/latest/historical_month_close_forecast_input_template.xlsx`에 차이가 있다.
- 위 차이는 이번 확인 기록에 남겨 둔다. 다음 배포 작업에서는 원본 작업 폴더와 로컬 배포 폴더 중 어느 쪽을 기준으로 삼을지 먼저 정하고, 의도한 파일만 동기화한 뒤 이 기록을 갱신한다.

## 배포 전 체크 순서

1. 로컬 배포 폴더에서 `git status --short`를 확인한다.
2. 배포할 파일만 스테이징한다.
3. 원본 작업 폴더와 로컬 배포 폴더의 관련 파일 해시가 의도대로 같은지 확인한다.
4. 테스트와 `app.py` 문법 확인을 실행한다.
5. 원격 `main`에 푸시한다.
6. 푸시 후 원격 `main`과 로컬 배포 폴더 HEAD가 같은지 확인하고, 앱 내용 기준 커밋과 주요 파일 해시를 이 문서에 갱신한다.
