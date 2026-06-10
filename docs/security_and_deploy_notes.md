# 보안 및 배포 메모

## 로컬 실행과 배포 차이

이 도구는 사용자가 영업 일정, 일별 목표, 누적 실적을 직접 입력해 월마감 예상실적과 보고 산출물을 만드는 내부 운영 도구다. 로컬 실행은 개인 PC 또는 통제된 업무 환경을 전제로 하며, 배포 환경은 접근 권한, 저장소 공개 범위, 로그 보관 정책을 별도로 검토해야 한다.

## Public Streamlit 배포

실제 영업실적, 목표, 계약 관련 메모가 포함될 수 있으므로 Public Streamlit 또는 외부 공개 URL에 운영 데이터를 올리는 방식은 금지 또는 강하게 비추천한다. 데모가 필요하면 익명화된 샘플 데이터만 사용한다.

## Private/사내망 배포

운영 공유가 필요하면 Private Streamlit, 사내망, VPN, SSO 등 접근 제어가 가능한 환경을 우선 사용한다. private 배포 또는 사내망 배포 전에는 보안 담당자의 검토를 받아야 한다.

## secrets.toml 관리 원칙

`.streamlit/secrets.toml`은 로컬 전용 파일이다. 실제 값은 GitHub, 외부 저장소, 감리 제출 패키지, 배포 zip에 포함하지 않는다. 공유 가능한 예시는 `.streamlit/secrets.example.toml`만 사용하며, 이 파일에는 placeholder 값만 둔다.

## 실제 영업데이터 관리

실제 고객명, 전화번호, 주소, 계약번호, 주민번호, 상세 계약 메모 등 민감정보는 테스트, 샘플, GitHub, 외부 저장소에 올리지 않는다. 운영 입력 파일은 원본을 직접 수정하지 않고, 필요한 경우 별도 복사본 또는 익명화 데이터로 검증한다.

## 감리 패키지 생성

감리 제출 패키지는 `tools/collect_audit_artifacts.py`로 생성한다. 기본 정책은 `outputs/latest/`만 포함하고, `outputs/archive_invalid/`와 민감 파일은 제외한다. 패키지에는 `audit_submit/manifest.md`가 포함되며, included/excluded 파일 목록과 `excluded_sensitive_files` 경로 목록만 기록한다. 민감 파일 내용은 기록하지 않는다.
