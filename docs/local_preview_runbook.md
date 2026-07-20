# 로컬 미리보기 실행 가이드

## 기본 실행

로컬 개발 및 익명 샘플 확인은 아래 명령을 사용합니다.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\start_streamlit_server.ps1
```

기본값은 `127.0.0.1:8501`과 `PRIVATE_DATA_MODE=local_demo`입니다. 이 모드는
현재 PC에서만 접속할 수 있으며 별도의 Private 데이터 저장소가 없어도 익명 샘플로
실행됩니다.

기본 미리보기는 기존 `runtime_storage`와 `outputs/saved_actuals.csv`를 삭제하거나
덮어쓰지 않고, 깨끗한 익명 샘플로 시작합니다. 기존 로컬 저장값을 확인해야 할 때만
다음 옵션을 사용합니다.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\start_streamlit_server.ps1 -UseSavedLocalData
```

포트를 바꾸려면 `-Port`를 지정합니다.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\start_streamlit_server.ps1 -Port 8502
```

## Private 저장소 모드

실제 운영 저장소 연동을 로컬에서 점검할 때만 `private` 모드를 명시합니다.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\start_streamlit_server.ps1 -DataMode private
```

이 경우 `.streamlit/secrets.toml` 또는 승인된 환경변수에 `PRIVATE_DATA_REPO`,
`PRIVATE_DATA_TOKEN`, `PRIVATE_DATA_BRANCH`, `PRIVATE_DATA_PREFIX`를 설정해야 합니다.
실제 값은 코드 저장소나 문서에 기록하지 않습니다.

## 안전 제한

- `local_demo`는 `127.0.0.1`, `localhost`, `::1`에서만 허용됩니다.
- 외부 주소에 바인딩할 때는 `-DataMode private`과 접속 비밀번호 설정이 필요합니다.
- Public Streamlit에는 실제 영업실적 파일을 업로드하지 않습니다.
- 마감일 판정은 입력 파일의 `is_close_day`만 사용합니다.
