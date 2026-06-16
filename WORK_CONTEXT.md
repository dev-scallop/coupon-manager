# 작업 맥락

## 작업 목적
- `dev-scallop/coupon-manager`에서 로그인 화면이 올바른 비밀번호 입력 후 멈추는 문제를 확인하고 수정한다.

## 중요한 사용자 선호와 금지사항
- 모든 답변은 한국어로 작성한다.
- 설명은 초보자도 이해하기 쉽게 짧고 명확하게 쓴다.
- 작업 전후로 이 파일을 최신 상태로 유지한다.

## 주요 파일과 폴더
- `index.html`: 쿠폰 관리 웹앱 전체 화면과 로그인/쿠폰 로직.
- `supabase-schema.sql`: 쿠폰 테이블과 Storage 정책 생성 SQL.
- `process-coupons.sh`, `upload-coupon.sh`: 쿠폰 처리/등록 보조 스크립트.

## 실행/검증 명령
- 로컬 실행:
  ```bash
  python -m http.server 8087 --bind 127.0.0.1
  ```
- 브라우저 접속:
  ```text
  http://127.0.0.1:8087/
  ```
- 스크립트 문법 및 SHA-256 예비 함수 확인:
  ```bash
  node -
  ```

## 마지막 산출물
- `index.html` 수정 완료.
- 원인: Supabase CDN이 만드는 전역 `supabase` 이름과 앱 코드의 `const supabase` 선언이 충돌해 전체 로그인 스크립트가 멈췄다.
- 수정: 내부 변수명을 `supabaseClient`로 바꾸고, Supabase 로딩/설정 오류를 화면에 표시하도록 처리했다.
- 보강: `crypto.subtle`이 없는 브라우저에서도 비밀번호 해시를 계산할 수 있도록 SHA-256 예비 함수를 추가했다.
- 검증: 브라우저에서 로그인 화면과 버튼 동작 확인, Node로 해시 함수 표준값과 로그인 성공 흐름 확인.

## 다음에 이어서 할 때 먼저 볼 것
- `index.html`의 `SUPABASE_ANON_KEY`가 현재 placeholder(`eyJhbG...oBao`)라 실제 Supabase 데이터 조회에는 전체 anon key가 필요하다.
- 로그인 문제가 다시 생기면 브라우저 콘솔에서 `Identifier 'supabase' has already been declared`가 다시 나오는지 먼저 확인한다.
