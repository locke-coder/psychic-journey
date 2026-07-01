# U06.1 L3 Pilot Protocol

## 1. Purpose

U06.1 기준본으로 제한된 내부 파일럿을 수행한다.

## 2. Data Restrictions

- 샘플 데이터만 사용
- 익명화 데이터만 사용
- 실제 고객명, 전화번호, 주소, 계약번호, 주민번호, 계좌번호, 실고객 식별자 사용 금지
- 실매출 원본 파일 업로드 금지
- 외부 URL 또는 Public Streamlit 배포 금지

## 3. Participant Scope

- LOCKE 단독 또는 1~3명 제한 내부 파일럿
- 팀 전체 실사용 금지
- L4 승인 전 정식 운영 금지

## 4. Feedback Classification

- S1: 즉시 중단급. 계산 오류, 민감정보 노출, 보안 위반, 데이터 손상, is_close_day 원칙 위반, 핵심 산식 훼손
- S2: L4 전 필수 처리. Excel 최신 컬럼 누락, CloseCycle cumulative columns 누락, 보고/운영 의사결정에 영향을 주는 산출물 오류
- S3: 파일럿 가능하나 개선 필요. 화면 설명 부족, 캡처 미확보, Git 기준버전 미확보, UX/문구 개선
- S4: 선택 개선. 디자인, 사소한 문구, 편의 기능, 향후 고도화 아이디어

## 5. L4 Entry Criteria

- S1 0건
- S2 0건 또는 명시적 waiver
- S3는 owner와 due date 지정
- S4는 backlog로 이관 가능
- pytest PASS
- Gate Runner ALL PASS
- 최신 Excel 산출물 검증 PASS
- 보안/배포 정책 확인

## 6. Close-Day Rule

- 마감일은 is_close_day 컬럼으로만 판단한다.
- day_name은 표시용으로만 사용할 수 있다.
- 요일, 날짜 패턴, weekday 계열 계산으로 마감일을 자동 추론하지 않는다.
- 입력표에 없는 날짜를 임의 생성하지 않는다.
