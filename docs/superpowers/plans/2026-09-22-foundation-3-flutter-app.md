# 기반 3 — Flutter 앱 골격과 재인증 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 시뮬레이터에서 로그인 → 초대 코드 합류 → 홈 → 매장 관리 → 계정 연결·해제·탈퇴까지 끝까지 도는 Flutter 앱을 만들고, 연결·해제·탈퇴 앞에 "최근 로그인 확인"(재인증)을 백엔드와 앱에 넣는다.

**Architecture:** 앱은 서버 데이터를 보여주는 얇은 클라이언트다. `core/`(설정·HTTP·저장소·라우터·오류) 위에 `design/`(토큰·글래스 브리지·기본 위젯 9개)과 `features/`(화면·상태·API 세 층)를 올린다. 상태는 Riverpod `AsyncNotifier`, 라우팅은 go_router 의 redirect 가드, 통신은 dio 다. 재인증은 액세스 토큰의 `auth_time` 클레임과 `core/security.py` 의 가드 하나로 끝난다 — 새 엔드포인트가 없다.

**Tech Stack:** Flutter 3.44.8 (Dart 3.x), flutter_riverpod 3.4.3, go_router 18.0.1, dio 5.11.1, flutter_secure_storage 11.2.0, liquid_glass_widgets 1.7.1, flutter_animate 4.5.2, kakao_flutter_sdk_user 2.0.1, google_sign_in 7.2.0, sign_in_with_apple 8.2.0, crypto(Apple nonce 해시 — Task 14) / 백엔드는 기존 스택(Python 3.13 · FastAPI · python-jose).

**Spec:** `docs/superpowers/specs/2026-09-20-foundation-design.md` — 6절(Flutter 앱 골격), 7절(오류 처리), 8.2·8.4절(테스트·완료 기준), 5.3·5.6·5.7절(토큰·연결·탈퇴). 함께 읽을 것: `_docs/decisions/003-account-lifecycle.md` 의 "계획 3으로 넘기는 것"과 "출시 차단 항목", `_docs/decisions/001-plan1-review-carryover.md` 11번(재사용 감지에 유예 없음).

## Global Constraints

언어·작업 규칙
- 주석·문서·테스트 이름·커밋 메시지는 한국어다. 화면 문구도 한국어다.
- **Hiss Haus 는 첫 입점 매장 이름이다.** 앱 이름·패키지명·문구에서 플랫폼 이름으로 쓰지 않는다. 플랫폼 이름은 "차곡노트"다.
- 커밋은 작업 단위로 로컬에만 한다. 푸시하지 않는다.
- 비밀값(토큰, 키, `.env*` 내용)을 로그·문서·테스트 실패 메시지·스크린샷에 남기지 않는다. 앱 코드에 `print`/`debugPrint`/dio `LogInterceptor` 로 요청·응답 본문이나 헤더를 찍지 않는다.
- 백엔드 명령은 전부 `infra/` 에서 `docker compose run --rm backend …` 로 돌린다. 맥에 파이썬 환경을 만들지 않는다. `alembic downgrade`, `docker compose down -v`, 볼륨 삭제는 하지 않는다.
- Flutter 명령은 전부 `app/` 에서 돌린다: `flutter analyze`(경고 0), `flutter test`.

앱 구조 (설계 6.1 — 그대로 지킨다)
- 폴더: `lib/core/{config,proxy,storage,router,error}`, `lib/design/{tokens,bridge,widgets}`, `lib/features/{auth,shop,account,home}/{screens,state,api}`, `lib/l10n`, `test/`.
- 기능 폴더 안은 **화면 · 상태 · API 클라이언트 세 층만** 둔다. 리포지토리·유스케이스·엔티티 계층을 만들지 않는다.
- 서버 응답의 필드명은 변환하지 않는다(`shop_id` 는 Dart 에서 `shopId` 로 받되 JSON 키는 그대로 읽는다). 모델은 평범한 클래스에 `fromJson` 을 직접 쓴다. **코드 생성기(build_runner, freezed, json_serializable, riverpod_generator, gen-l10n)를 도입하지 않는다.**
- 화면 코드는 `liquid_glass_widgets` 를 직접 import 하지 않는다. `design/widgets` 만 쓴다. 글래스 패키지를 import 하는 파일은 `lib/design/bridge/` 안에만 있다.
- 의존 패키지는 설계 6.1 의 9개와 `crypto` 하나(Apple nonce 의 SHA-256 — Task 14)뿐이다. Rive·Lottie 와 그 밖의 패키지를 더하지 않는다(테스트 전용도 SDK 에 있는 것만).
- 패키지 ID 는 임시값 `com.chagocnote.app`, 앱 표시 이름은 `차곡노트`.

네이티브 앱 (사용자 지시 2026-09-22 — 웹뷰 방식 금지)
- `webview_flutter`·`flutter_inappwebview` 같은 웹뷰 패키지를 넣지 않는다. 어떤 화면도 인앱 웹뷰로 만들지 않는다.
- 소셜 로그인은 네이티브 경로를 쓴다: 카카오는 카카오톡 앱 전환(`loginWithKakaoTalk`)을 먼저 시도하고, 카카오톡이 없을 때만 SDK 의 시스템 인증 세션(`loginWithKakaoAccount`)으로 간다. 구글은 네이티브 SDK(`GoogleSignIn.instance.authenticate()`)다. **Apple 버튼은 iOS 에서만 보인다** — Android 의 Apple 로그인은 웹 흐름뿐이다.

디자인 (설계 6.2 — 값은 그대로 복사한다)
- 색: 바탕 `#f5f5f5` → `#ececec` 세로 그라데이션, 글자·포인트 `#161616` 한 가지, 보조 `#8d8d8d`, 선 `#dcdcdc`. 다른 색을 만들지 않는다. 색은 사진이 담당한다.
- 글꼴: 본문 Pretendard, 큰 숫자·영문 제목 Bodoni Moda, 한글 제목 마루 부리. 세 글꼴 모두 SIL OFL 이고 앱에 포함한다.
- 글래스는 떠 있는 조작 계층(탭바·시트·카드)에만 쓴다. 스크롤되는 콘텐츠에는 쓰지 않는다. 투명도는 낮게, 테두리는 또렷하게.
- 움직임은 스프링 물리다. 누르는 위젯은 0.96배로 눌렸다가 스프링으로 돌아오고 가벼운 햅틱을 준다. 시스템 "동작 줄이기"가 켜져 있으면 스프링을 페이드로, "투명도 줄이기"가 켜져 있으면 글래스를 불투명한 면으로 대체한다.
- 기준 목업: `.superpowers/brainstorm/67059-1789889527/content/mono-tone.html` (git 무시 대상이라 이 맥에만 있다).

세션과 토큰 (사용자 결정 — 다시 제안하지 않는다)
- 리프레시 토큰 재사용 감지에는 유예가 없다. 그래서 앱은 **갱신 요청을 동시에 하나만** 보내고, **갱신 요청은 어떤 이유로 실패해도 자동으로 다시 보내지 않는다.** Riverpod 3 의 프로바이더 자동 재시도를 `ProviderScope(retry: …)` 로 끈다.
- 갱신이 401/403 으로 끝나면 저장된 토큰을 지우고 로그인 화면으로 보내며 "보안을 위해 다시 로그인해 주세요"를 보여 준다. 네트워크 오류면 토큰을 지우지 않고 "다시 시도" 안내를 보여 준다.
- 리프레시 토큰은 불투명한 문자열로 다룬다(앞의 `{user_id}.` 를 해석하지 않는다). 토큰은 `flutter_secure_storage` 에만 둔다.
- 로그인 수단 해제의 응답에 든 새 토큰을 **다른 어떤 일보다 먼저** 저장한다(옛 토큰은 그 순간 전부 죽었다).
- 구글 연결 끊기는 서버가 아니라 앱이 한다: 구글 수단 해제가 성공한 뒤 `GoogleSignIn.instance.disconnect()`.
- 재인증은 "최근 로그인 확인"이다: 소셜 로그인으로 받은 액세스 토큰에만 `auth_time` 이 있고, 연결·해제·탈퇴는 `auth_time` 이 300초 이내일 때만 받는다. 아니면 `403 REAUTH_REQUIRED`. 앱은 소셜 로그인을 한 번 더 한 뒤 **한 번만** 다시 요청한다.

API (이미 있는 백엔드 — 바꾸지 않는다. 재인증 작업만 예외)
- 게이트웨이 `http://127.0.0.1:8080` (iOS 시뮬레이터), `http://10.0.2.2:8080` (Android 에뮬레이터). `--dart-define=API_BASE_URL=…` 로 주입한다.
- 오류 본문은 언제나 `{"code": "...", "message": "..."}`. 앱은 `code` 로 문구를 고른다(서버 `message` 는 모르는 코드일 때만 쓴다).
- 개발 환경 전용 제공자 `dev`: `POST /v1/auth/social {"provider":"dev","token":"<이름>"}` — 입력한 이름으로 바로 로그인된다. 카카오·구글·Apple 키가 아직 없으므로 **개발과 흐름 확인은 `dev` 로 한다.** `dev` 로그인 버튼은 `APP_ENV=dev` 일 때만 보인다.

| 메서드 · 경로 | 요청 | 응답 |
|---|---|---|
| `POST /v1/auth/social` | `{provider, token, authorization_code?, nonce?, display_name?}` | 200 `{access_token, refresh_token, token_type, expires_in, user_id, is_new_user}` |
| `POST /v1/auth/refresh` | `{refresh_token}` | 200 `{access_token, refresh_token, token_type, expires_in}` |
| `POST /v1/auth/logout` | `{refresh_token}` | 204 |
| `POST /v1/auth/identities` | `{provider, token, authorization_code?, nonce?}` | 200 `{identities: [string]}` |
| `DELETE /v1/auth/identities/{provider}` | — | 200 `{identities, access_token, refresh_token, token_type, expires_in}` |
| `DELETE /v1/auth/account` | `{confirm_close_shops?: bool}` (JSON `true`/`false` 만, 문자열 금지) | 204 |
| `GET /v1/me` | — | 200 `{id, display_name, profile_image_url, identities: [string], shops: [{shop_id, shop_name, role}]}` |
| `POST /v1/invites/accept` | `{code}` | 200 `{shop_id, shop_name, role, member_id}` |
| `GET /v1/shops/{shop_id}/members` | — | 200 `[{member_id, user_id, display_name, profile_image_url, role, joined_at}]` |
| `POST /v1/shops/{shop_id}/invites` | — | 201 `{code, role, expires_at}` |
| `PATCH /v1/shops/{shop_id}/members/{member_id}` | `{role: "owner"\|"staff"}` | 200 `{member_id, user_id, role}` |
| `DELETE /v1/shops/{shop_id}/members/{member_id}` | — | 204 |
| `GET /v1/shops/{shop_id}/settings` | — | 200 `{shop_id, name, business_type, phone, address, timezone}` |
| `PUT /v1/shops/{shop_id}/settings` | `{name, phone?, address?}` | 200 (같은 모양) |

- 역할은 `owner`(사장)·`staff`(직원) 둘이다. `member:manage`(초대·역할 변경·내보내기)와 `shop:update`(매장 정보 수정)는 사장만 가진다. 멤버 목록과 매장 정보 보기는 멤버 누구나 된다. 앱은 `role == "owner"` 일 때만 관리 메뉴를 보여 준다 — **보안 경계는 서버의 403 이고, 메뉴 숨김은 편의다.**
- 오류 코드: `UNAUTHENTICATED`(401), `PROVIDER_VERIFICATION_FAILED`(401), `ACCOUNT_SUSPENDED`·`NOT_A_MEMBER`·`PERMISSION_DENIED`·`SHOP_CLOSED`·`SHOP_SUSPENDED`·`REAUTH_REQUIRED`(403), `MEMBER_NOT_FOUND`·`IDENTITY_NOT_FOUND`(404), `INVITE_INVALID`·`INVITE_EXPIRED`·`INVITE_EXHAUSTED`·`PROVIDER_NOT_SUPPORTED`(400), `LAST_OWNER`·`ALREADY_A_MEMBER`·`IDENTITY_ALREADY_LINKED`·`PROVIDER_ALREADY_LINKED`·`LAST_IDENTITY`·`OWNERSHIP_TRANSFER_REQUIRED`·`SHOP_CLOSE_CONFIRM_REQUIRED`(409), `VALIDATION_ERROR`(422), `TOO_MANY_ATTEMPTS`(429).

결정 기록 003 에서 넘어온 앱의 의무
- `NOT_A_MEMBER` 를 받으면 그 매장을 기기에서 바로 지우지 말고 `/v1/me` 를 다시 받아 판단한다(강등된 멤버도 이 코드를 받는다).
- 초대 수락에서 401 `UNAUTHENTICATED` 가 나오면 갱신 후 재시도가 아니라 로그인 화면으로 보낸다(탈퇴·정지된 계정이다).
- 회원 탈퇴는 204 와 401 을 둘 다 "탈퇴 완료"로 처리한다. `DELETE` 본문이 실제로 전송되는지 테스트로 확인한다.

## 이 계획에서 새로 정한 것

1. **재인증(사용자 결정 2026-09-22)**: 액세스 토큰에 `auth_time`(초 단위 UNIX 시각)을 넣는다. 소셜 로그인이 발급한 토큰에만 있고, 갱신이 발급한 토큰에는 없다. 해제가 발급한 새 토큰은 **요청에 쓰인 토큰의 `auth_time` 을 그대로 물려받는다** — 해제를 되풀이해 "최근 로그인"을 늘릴 수 없게 하기 위해서다. 기준은 300초다.
2. **문구는 `lib/l10n/app_strings.dart` 의 상수 클래스 하나**에 모은다. `gen-l10n` 은 코드 생성기라 도입하지 않는다. 다국어가 필요해지면 그때 바꾼다.
3. **소셜 로그인 버튼은 설정이 있는 것만 보인다**: `KAKAO_NATIVE_APP_KEY`, `GOOGLE_IOS_CLIENT_ID`/`GOOGLE_SERVER_CLIENT_ID`, `APPLE_SIGN_IN_ENABLED`, `APP_ENV` 를 `--dart-define` 으로 받는다. 값이 없으면 그 버튼은 없다. 지금은 `APP_ENV=dev` 의 "개발용 로그인"만 실제로 동작한다.
4. **`crypto` 를 열 번째 의존성으로 더한다.** 백엔드는 Apple 토큰의 `nonce` 가 `sha256(원본)` 인지 확인하므로 앱에서 SHA-256 이 필요하다. dart-lang 공식 패키지다.
5. **카카오·구글·Apple 의 네이티브 설정은 키가 생길 때 한다**(설계 8.3 — 등록은 사용자만 할 수 있다). 이 계획은 Dart 쪽 구현과 `app/NATIVE-SETUP.md` 까지다.
6. **테스트와 "투명도 줄이기"에서는 글래스를 불투명한 면으로 그린다.** 셰이더는 `flutter test` 환경에서 믿을 수 없다. 골든 테스트는 불투명 대체 모습을 찍는다(설계 8.2 의 "대체 모습도 찍는다"를 이렇게 충족한다).

## 이 계획의 코드는 어떻게 검증했나

계획 2-1·2-2 에서는 검증 없이 쓴 계획서 코드에서 결함이 많이 나왔다(2-2 는 13개 작업 중 11개). 그래서 이번에는 **계획을 쓰기 전에 저장소 밖의 참조 프로젝트에서 앱 전체를 한 번 만들어 보았다.** Task 1~14·16 의 Dart 코드와 테스트는 그 프로젝트의 작업별 커밋에서 그대로 가져온 것이고, 마지막 상태에서 `flutter analyze` 0건 · `flutter test` 175개 통과 · `flutter build ios --simulator --debug` 와 `flutter build apk --debug` 통과를 확인했다(Flutter 3.44.8 · Xcode 27, 이 맥). Task 1 의 셸 명령도 임시 프로젝트에서 돌려 보았다. **백엔드 작업(Task 15)의 코드는 이렇게 검증하지 않았다** — 실제 파일을 읽고 썼을 뿐이다.

그래도 규칙은 같다. **검토자는 이 계획서의 코드를 검토되지 않은 것으로 본다.** 참조 프로젝트는 "컴파일되고 자기 테스트를 통과한다"까지만 보장한다. 테스트가 옳은 것을 확인하는지, 빠진 시나리오가 없는지는 보장하지 않는다. 구현자는 코드를 옮겨 적은 뒤 반드시 테스트를 돌리고, 각 작업의 "판별력 확인" 단계를 실제로 한다.

수정하는 파일은 `diff` 블록으로 보인다 — `-` 줄을 지우고 `+` 줄을 더한다.

## 점검표 — 앱이 틀리기 쉬운 곳

계획 2-1·2-2 의 교훈: 작업별 검토가 "계획서와 일치"만 보면 계획서 코드의 구멍이 그대로 통과한다. **검토자는 이 계획서의 코드를 검토되지 않은 것으로 보고, 아래 시나리오와 설계 문서를 기준으로 판단한다.**

| # | 시나리오 | 막는 곳 | 확인하는 테스트 |
|---|---|---|---|
| S1 | 화면 셋이 동시에 401 을 받는다 → 갱신이 세 번 나가면 재사용 감지로 모든 기기 로그아웃 | `ApiClient` 단일 갱신 | Task 5 `동시에 3개 요청이 401을 받아도 리프레시는 한 번만 나간다` |
| S2 | 갱신 요청이 타임아웃 → 자동 재전송하면 (응답만 잃은 경우) 재사용으로 판정 | `ApiClient` — 갱신은 재전송하지 않는다, Riverpod retry 끔 | Task 5 `리프레시가 타임아웃되면 토큰은 유지되고 … 리프레시는 한 번만 나간다`·`리프레시가 게이트웨이 오류(502·503·504)면 …`, Task 6 `ProviderContainer.test(retry: …) 이면 build() 가 실패해도 정확히 한 번만 호출된다` |
| S3 | 갱신이 401 → 죽은 토큰을 계속 들고 무한 401 | 토큰 삭제 + `onSessionEnded` | Task 5 `리프레시가 401을 받으면 토큰을 지우고 onSessionEnded를 한 번만 부르며 …`, Task 6 `session_ended_wiring_test`, Task 7 `홈에 있는 중 endSession 이 호출되면 로그인 화면으로 밀려난다` |
| S4 | 토큰이 로그·크래시 리포트에 남는다 | 로깅 인터셉터 금지, 모델에 `toString` 없음 | Task 5 검토 항목, Task 17 `grep` 확인 |
| S5 | 해제 응답의 새 토큰을 저장하기 전에 다른 요청이 옛 토큰으로 나간다 → 401 → 갱신(옛 리프레시) → 실패 → 로그아웃 | `AccountApi.unlink` 가 응답을 받자마자 저장 | Task 12 `응답의 새 토큰을 먼저 저장한 뒤 identities 를 돌려준다(S5)` + 컨트롤러의 순서 고정 테스트, Task 16 `unlink 이 재인증을 거쳐도 해제 응답의 토큰이 마지막에 저장된다(이긴다)` |
| S6 | 재인증에서 **다른 계정**으로 로그인한다 → 세션이 조용히 남의 계정으로 바뀐다 | 재인증 결과의 `user_id` 확인, 다르면 그 세션을 로그아웃하고 거절 | Task 16 `S6 — 다른 계정으로 재로그인하면 저장된 토큰은 그대로고 그 세션은 로그아웃된다` |
| S7 | 탈퇴 확인값이 문자열 `"true"` 로 나간다 → 422 | 본문을 Dart `bool` 로 만들고 본문 전송을 테스트 | Task 12 `confirmCloseShops 가 true 면 JSON 불리언 본문을 보낸다` · `… false 면 본문 없이 보낸다`, Task 5 `DELETE 요청이 JSON 바디를 실제로 보낸다` |
| S8 | 내보내진 직원의 앱이 옛 매장을 계속 골라 둔다 | `NOT_A_MEMBER` → `/v1/me` 재조회 → 라우터 재평가 | Task 10 `NOT_A_MEMBER 면 reloadMe 를 부른다 — 매장이 남아있으면 그대로 머무른다` · `… 매장이 사라졌으면 라우터가 내보낸다` |
| S9 | 직원에게 관리 메뉴가 보인다 / 사장에게 안 보인다 | `role == owner` 분기 | Task 10 `직원은 관리 UI가 안 보인다`, Task 11 의 직원 읽기 전용 테스트 |
| S10 | 로그아웃 상태에서 `/settings/...` 로 들어간다 | 라우터 redirect | Task 7 `로그아웃 상태로 /settings/members 딥링크를 열어도 로그인 화면으로 간다` |
| S11 | 릴리스 빌드에 개발용 로그인 버튼이 남는다 | `AppConfig.isDev` 분기 | Task 8 `appEnv 가 dev 가 아니면 개발용 로그인 버튼이 없다` |
| S12 | 탈퇴가 401 로 끝났는데 앱이 "실패"로 본다 | 204·401 모두 완료 처리, 완료 뒤에는 `SignedOut()`(만료 띠 없음) | Task 12 `401 은 이미 완료된 탈퇴로 보고 정상 종료한다(S12)`, Task 13 의 탈퇴 화면 테스트 |
| R1 | 갱신으로 받은 토큰으로 연결·해제·탈퇴 → 통과하면 재인증이 무의미 | 갱신 발급에는 `auth_time` 없음 | Task 15 `갱신으로_받은_토큰은_REAUTH_REQUIRED_다` |
| R2 | 해제를 되풀이해 "최근 로그인"을 계속 늘린다 | 해제 발급은 원래 `auth_time` 을 물려받는다 | Task 15 `해제가_준_토큰은_원래_로그인_시각을_물려받는다` |
| R3 | 로그인한 지 300초 넘은 토큰 | `require_recent_login` | Task 15 `로그인한_지_오래된_토큰은_403_이다` |
| R4 | 재인증 가드가 탈퇴·정지 확인을 빠뜨린다 | 가드가 `get_current_user_id` 와 같은 확인을 공유 | Task 15 `정지된_계정은_최근_로그인이어도_403_ACCOUNT_SUSPENDED_다` |
| R5 | 나중에 추가한 민감 라우트가 가드를 빠뜨린다 | 구조 테스트 | Task 15 `route_inspection` 규칙 |

## 파일 지도

```
app/                                   # 새로 만든다 (flutter create)
├── pubspec.yaml · analysis_options.yaml · CLAUDE.md · NATIVE-SETUP.md · tool/run_dev.sh
├── assets/fonts/                      # Pretendard · BodoniModa · MaruBuri (OFL)
├── lib/
│   ├── main.dart · app.dart
│   ├── core/
│   │   ├── config/app_config.dart            # --dart-define 값
│   │   ├── error/api_exception.dart          # {code,message} → 예외
│   │   ├── error/error_messages.dart         # code → 한국어 문구
│   │   ├── storage/token_store.dart          # 토큰 (보안 저장소)
│   │   ├── storage/prefs_store.dart          # 마지막으로 고른 매장
│   │   ├── proxy/api_client.dart             # 토큰 첨부 · 단일 갱신 · 한 번 재시도
│   │   ├── proxy/providers.dart              # ApiClient · 저장소 프로바이더
│   │   └── router/{app_router,screen_keys}.dart   # go_router + redirect 가드
│   ├── design/
│   │   ├── tokens/{app_colors,app_typography,app_spacing,app_radius,app_shadows,app_springs}.dart
│   │   ├── bridge/glass_surface.dart         # 글래스 교체 지점 (여기만 패키지를 import)
│   │   └── widgets/{pressable,app_button,app_fab,app_glass_bar,app_glass_card,app_sheet,
│   │                app_segment,app_photo_tile,app_big_date,app_chip}.dart
│   ├── features/
│   │   ├── auth/{api/{auth_api,me_api,invite_api,social_sign_in,kakao_sign_in,google_sign_in_adapter,apple_sign_in,apple_nonce}.dart,
│   │   │         state/{session,session_gateway,session_controller,auth_providers,social_sign_ins}.dart,
│   │   │         screens/{splash,login,invite_code,shop_select}_screen.dart}
│   │   ├── home/{screens/home_shell.dart, state/today_provider.dart}
│   │   ├── shop/{api/shop_api.dart, state/{shop_providers,shop_errors,members_controller,shop_settings_controller}.dart,
│   │   │         screens/{settings,members,shop_settings}_screen.dart}
│   │   └── account/{api/account_api.dart, state/{account_controller,withdraw_controller,reauth}.dart,
│   │                screens/{account,withdraw}_screen.dart}
│   └── l10n/app_strings.dart
└── test/                              # lib 와 같은 모양 + support/ (폰트 로더, 가짜 어댑터, 가짜 게이트웨이)

backend/                               # 재인증 (Task 15)
├── core/security.py                           # AccessClaims · require_recent_login
├── apps/auth/app/ports/output/token_issuer_port.py · adapter/outbound/gateways/jwt_token_issuer.py
├── apps/auth/app/services/session_issuer.py
├── apps/auth/app/use_cases/{social_login,unlink_identity}_interactor.py · dtos/unlink_identity_dto.py
├── apps/auth/adapter/inbound/api/v1/{link_identity,unlink_identity,withdraw}_router.py
└── tests/route_inspection.py · tests/integration/test_reauth_wiring.py

문서: docs/superpowers/specs/2026-09-20-foundation-design.md (5.3·5.6·5.7·6·7절),
      _docs/decisions/004-flutter-app-and-reauth.md, _docs/harness.md, CLAUDE.md, README.md
```

---

### Task 1: Flutter 프로젝트 생성과 기본 설정

**Files:**
- Create: `app/` 전체 (`flutter create`), `app/CLAUDE.md`
- Modify: `app/pubspec.yaml`, `app/analysis_options.yaml`, `app/ios/Runner/Info.plist`, `app/ios/Runner.xcodeproj/project.pbxproj`, `app/android/app/build.gradle.kts`, `app/android/app/src/main/AndroidManifest.xml`, `app/android/app/src/debug/AndroidManifest.xml`
- Create: `app/lib/core/config/app_config.dart`, `app/lib/main.dart`(자리 표시)
- Test: `app/test/core/config/app_config_test.dart`, `app/test/smoke_test.dart`

**Interfaces:**
- Consumes: 없음 (첫 작업). 브랜치 `feat/foundation-3-flutter-app` 은 컨트롤러가 이미 만들었다.
- Produces:
  - Dart 패키지 이름 `chagocnote` (`import 'package:chagocnote/…'`), 패키지 ID `com.chagocnote.app`, 앱 표시 이름 `차곡노트`
  - `class AppConfig { const AppConfig({required String apiBaseUrl, required String appEnv, String kakaoNativeAppKey = '', String googleIosClientId = '', String googleServerClientId = '', bool appleSignInEnabled = false}); factory AppConfig.fromEnvironment(); bool get isDev; bool get kakaoEnabled; bool get googleEnabled; }`
  - 의존 패키지 9개가 설치된 `pubspec.yaml`, iOS·Android 디버그 빌드가 되는 네이티브 설정

계획을 쓰기 전에 확인한 사실 (이 맥, Flutter 3.44.8 · Xcode 27)
- 패키지 9개는 함께 풀린다: flutter_riverpod 3.4.3, go_router 18.0.1, dio 5.11.1, flutter_secure_storage 11.2.0, kakao_flutter_sdk_user 2.0.1, sign_in_with_apple 8.2.0, google_sign_in 7.2.0, liquid_glass_widgets 1.7.1, flutter_animate 4.5.2.
- **`flutter create` 가 만드는 iOS 배포 대상 13.0 으로는 빌드가 실패한다**(`The iOS Simulator deployment target … is set to 13.0, but the range of supported deployment target versions is 15.0 to 27.0.x`). 15.0 으로 올리면 9개 패키지를 넣은 채로 `flutter build ios --simulator --debug` 가 통과한다. Android 는 그대로 `flutter build apk --debug` 가 통과한다.
- 네이티브 의존성은 Swift Package Manager 로 풀린다. `ios/Podfile` 은 생기지 않는다 — 만들지 않는다.
- `flutter pub add` 직후 go_router 의 전이 의존성 `material_ui`·`cupertino_ui` 가 **회수된(retracted) 버전**으로 고정되어 `awaitNotRequired` 미정의로 컴파일이 실패한 적이 있다. 그러면 `pubspec.lock` 을 지우고 `flutter pub get` 을 다시 한다(확인된 정상 버전: `material_ui 1.2.0`, `cupertino_ui 1.0.2`).

- [ ] **Step 1: 프로젝트를 만든다**

Run (저장소 루트에서):
```bash
flutter create --org com.chagocnote --project-name chagocnote --platforms ios,android app
cd app
flutter pub add flutter_riverpod go_router dio flutter_secure_storage kakao_flutter_sdk_user sign_in_with_apple google_sign_in liquid_glass_widgets flutter_animate
rm test/widget_test.dart
```
Expected: `Changed … dependencies!`. `flutter pub get` 출력에 `retracted` 가 보이면 위의 네 번째 사실대로 한다.

- [ ] **Step 2: 패키지 ID · 앱 이름 · 배포 대상 · 로컬 네트워크**

Run (`app/` 에서):
```bash
# 패키지 ID: com.chagocnote.chagocnote → com.chagocnote.app (Android namespace 는 Kotlin 패키지 경로라 그대로 둔다)
sed -i '' 's/com\.chagocnote\.chagocnote/com.chagocnote.app/g' ios/Runner.xcodeproj/project.pbxproj
sed -i '' 's/applicationId = "com.chagocnote.chagocnote"/applicationId = "com.chagocnote.app"/' android/app/build.gradle.kts
# 앱 표시 이름
/usr/libexec/PlistBuddy -c "Set :CFBundleDisplayName 차곡노트" ios/Runner/Info.plist
sed -i '' 's/android:label="chagocnote"/android:label="차곡노트"/' android/app/src/main/AndroidManifest.xml
# iOS 배포 대상 (Xcode 27 은 15.0 미만을 받지 않는다)
sed -i '' 's/IPHONEOS_DEPLOYMENT_TARGET = 13.0;/IPHONEOS_DEPLOYMENT_TARGET = 15.0;/g' ios/Runner.xcodeproj/project.pbxproj
# 개발 중에는 http://127.0.0.1:8080 에 붙는다. iOS 는 로컬 네트워크의 평문 HTTP 만 허용한다 (임의 도메인의 평문은 계속 막힌다)
/usr/libexec/PlistBuddy -c "Add :NSAppTransportSecurity dict" -c "Add :NSAppTransportSecurity:NSAllowsLocalNetworking bool true" ios/Runner/Info.plist
plutil -lint ios/Runner/Info.plist
grep -c "com.chagocnote.app" ios/Runner.xcodeproj/project.pbxproj
```
Expected: `ios/Runner/Info.plist: OK`, 마지막 줄 `6`.

`android/app/src/main/AndroidManifest.xml` 의 `<manifest …>` 바로 아래에 더한다(릴리스 빌드도 네트워크를 쓴다):
```xml
    <uses-permission android:name="android.permission.INTERNET"/>
```
`android/app/src/debug/AndroidManifest.xml` 을 아래로 바꾼다 — 에뮬레이터에서 `http://10.0.2.2:8080` 으로 붙기 위한 평문 허용은 **디버그 빌드에만** 둔다:
```xml
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <uses-permission android:name="android.permission.INTERNET"/>
    <!-- 개발용 게이트웨이(http://10.0.2.2:8080)에 붙기 위한 평문 허용. 릴리스 매니페스트에는 없다. -->
    <application android:usesCleartextTraffic="true"/>
</manifest>
```

- [ ] **Step 3: 분석 규칙**

`app/analysis_options.yaml`:
```yaml
include: package:flutter_lints/flutter.yaml

analyzer:
  errors:
    # 토큰이 로그에 남는 사고를 막는다. print 는 오류로 취급한다.
    avoid_print: error

linter:
  rules:
    avoid_print: true
    prefer_single_quotes: true
    require_trailing_commas: false
```

- [ ] **Step 4: 설정값 — 실패하는 테스트**

`app/test/core/config/app_config_test.dart`:
```dart
import 'package:chagocnote/core/config/app_config.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('아무 값도 주지 않으면 닫힌 쪽이 기본값이다', () {
    final config = AppConfig.fromEnvironment();
    expect(config.apiBaseUrl, 'http://127.0.0.1:8080');
    expect(config.appEnv, 'prod');
    expect(config.isDev, isFalse);
    expect([config.kakaoEnabled, config.googleEnabled, config.appleSignInEnabled], [false, false, false]);
  });

  test('dev 환경과 키가 있으면 해당 로그인 수단이 켜진다', () {
    const config = AppConfig(
      apiBaseUrl: 'http://10.0.2.2:8080',
      appEnv: 'dev',
      kakaoNativeAppKey: 'k',
      googleServerClientId: 'g',
      appleSignInEnabled: true,
    );
    expect(config.isDev, isTrue);
    expect([config.kakaoEnabled, config.googleEnabled, config.appleSignInEnabled], [true, true, true]);
  });
}
```

`app/test/smoke_test.dart`:
```dart
import 'package:chagocnote/main.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('앱이 뜨고 이름이 보인다', (tester) async {
    await tester.pumpWidget(const BootstrapApp());
    expect(find.text('차곡노트'), findsOneWidget);
  });
}
```

Run: `flutter test`
Expected: FAIL — `Not found: 'package:chagocnote/core/config/app_config.dart'`

- [ ] **Step 5: 구현**

`app/lib/core/config/app_config.dart`:
```dart
/// 빌드 시점에 `--dart-define`으로 주입하는 앱 설정.
///
/// 비밀값이 아니라 클라이언트에 이미 공개되는 값(API 주소, 소셜 로그인의
/// 공개 클라이언트 id 등)만 담는다. 진짜 비밀(개인키 등)은 여기 두지 않는다.
class AppConfig {
  const AppConfig({
    required this.apiBaseUrl,
    required this.appEnv,
    this.kakaoNativeAppKey = '',
    this.googleIosClientId = '',
    this.googleServerClientId = '',
    this.appleSignInEnabled = false,
  });

  /// `--dart-define`으로 넘어온 값을 읽는다. `APP_ENV`의 기본값이 `prod`인 것은
  /// 의도한 것이다 — 보안 게이트는 기본으로 닫혀 있어야 한다.
  factory AppConfig.fromEnvironment() => const AppConfig(
        apiBaseUrl: String.fromEnvironment(
          'API_BASE_URL',
          defaultValue: 'http://127.0.0.1:8080',
        ),
        appEnv: String.fromEnvironment('APP_ENV', defaultValue: 'prod'),
        kakaoNativeAppKey: String.fromEnvironment('KAKAO_NATIVE_APP_KEY'),
        googleIosClientId: String.fromEnvironment('GOOGLE_IOS_CLIENT_ID'),
        googleServerClientId: String.fromEnvironment(
          'GOOGLE_SERVER_CLIENT_ID',
        ),
        appleSignInEnabled: bool.fromEnvironment('APPLE_SIGN_IN_ENABLED'),
      );

  final String apiBaseUrl;
  final String appEnv;
  final String kakaoNativeAppKey;
  final String googleIosClientId;
  final String googleServerClientId;
  final bool appleSignInEnabled;

  bool get isDev => appEnv == 'dev';
  bool get kakaoEnabled => kakaoNativeAppKey.isNotEmpty;
  bool get googleEnabled => googleServerClientId.isNotEmpty;
}
```

`app/lib/main.dart` (Task 7 이 진짜 진입점으로 바꾼다):
```dart
import 'package:flutter/material.dart';

void main() => runApp(const BootstrapApp());

/// 골격만 있는 자리 표시 앱. 라우터가 들어오면(Task 7) 사라진다.
class BootstrapApp extends StatelessWidget {
  const BootstrapApp({super.key});

  @override
  Widget build(BuildContext context) {
    return const MaterialApp(
      title: '차곡노트',
      home: Scaffold(body: Center(child: Text('차곡노트'))),
    );
  }
}
```

- [ ] **Step 6: 통과와 빌드를 확인한다**

Run:
```bash
flutter analyze
flutter test
flutter build ios --simulator --debug
flutter build apk --debug
```
Expected: `No issues found!`, `All tests passed!` (3개), `✓ Built build/ios/iphonesimulator/Runner.app`, `✓ Built build/app/outputs/flutter-apk/app-debug.apk`. 빌드는 각각 수 분 걸린다. 2분 넘게 **출력이 멈춰 있으면** 멈추고 BLOCKED 로 보고한다.

- [ ] **Step 7: `app/CLAUDE.md` 와 커밋**

`app/CLAUDE.md`:
```markdown
# CLAUDE.md — 차곡노트 앱 (Flutter)

저장소 루트의 `CLAUDE.md` 를 먼저 읽는다. 여기는 앱에만 해당하는 규칙이다.

## 꼭 지킬 것

- **웹뷰 방식 금지.** 웹뷰 패키지를 넣지 않고, 어떤 화면도 인앱 웹뷰로 만들지 않는다. 소셜 로그인도 네이티브 경로다(Apple 버튼은 iOS 만).
- 기능 폴더(`lib/features/<기능>/`) 안은 `screens/` · `state/` · `api/` 세 층만 둔다.
- 서버 응답의 필드명은 변환하지 않는다. 모델은 평범한 클래스에 `fromJson` 을 직접 쓴다. 코드 생성기를 도입하지 않는다.
- `liquid_glass_widgets` 는 `lib/design/bridge/` 안에서만 import 한다. 화면은 `lib/design/widgets` 만 쓴다.
- 토큰을 로그에 남기지 않는다. `print`·`debugPrint`·dio `LogInterceptor` 를 쓰지 않는다(`avoid_print` 는 오류다).
- 리프레시 토큰 재사용에는 유예가 없다. 갱신 요청은 동시에 하나만, 실패한 갱신은 자동으로 다시 보내지 않는다. `ProviderScope` 의 `retry` 는 꺼 둔다.
- Hiss Haus 는 첫 입점 매장 이름이다. 앱 이름은 "차곡노트"다.

## 명령어 (`app/` 에서)

    flutter analyze                     # 경고 0
    flutter test                        # 골든 포함
    flutter test --update-goldens       # 골든을 의도해서 바꿀 때만
    tool/run_dev.sh                     # 개발용 실행 (APP_ENV=dev, 게이트웨이 http://127.0.0.1:8080)
```

```bash
git add app
git commit -m "feat(app): Flutter 프로젝트 골격 — 패키지 9종, 패키지 ID, iOS 15.0, 로컬 네트워크 허용"
```

### Task 2: 디자인 기반 — 글꼴, 토큰, 테마, 글래스 브리지, 누르는 효과

**Files:**
- Create: `app/assets/fonts/PretendardVariable.ttf`, `BodoniModa-VariableFont.ttf`, `MaruBuri-Regular.ttf`, `app/assets/fonts/LICENSES/{Pretendard,BodoniModa,MaruBuri}-OFL.txt`
- Modify: `app/pubspec.yaml` (`fonts:` 블록)
- Create: `app/lib/design/tokens/{app_colors,app_typography,app_spacing,app_radius,app_shadows,app_springs}.dart`, `app/lib/design/app_theme.dart`
- Create: `app/lib/design/bridge/glass_surface.dart`, `app/lib/design/bridge/glass_setup.dart`
- Create: `app/lib/design/widgets/pressable.dart`
- Test: `app/test/flutter_test_config.dart`, `app/test/support/load_fonts.dart`, `app/test/support/golden_frame.dart`, `app/test/design/glass_surface_test.dart`, `pressable_test.dart`, `import_boundary_test.dart`

**Interfaces:**
- Consumes: Task 1 의 프로젝트와 의존성 `liquid_glass_widgets`
- Produces:
  - 글꼴 패밀리 `Pretendard`, `BodoniModa`, `MaruBuri`
  - `AppColors.backgroundTop/backgroundBottom/ink/secondary/line/white/backgroundGradient`, `AppTypography.body/bodyStrong/caption/titleKo/titleEn/bigNumeral/italicLabel`, `AppSpacing.xs…xxl`(4·8·12·16·24·32), `AppRadius.sm…pill`(8·12·16·24·999), `AppShadows.soft/floating`, `AppSprings.press/settle/fadeDuration`
  - `ThemeData appTheme()`, `AppBackground({required Widget child})`
  - `GlassSurface({required Widget child, BorderRadius borderRadius, EdgeInsetsGeometry? padding})`, `GlassBridge({required GlassSurfaceFactory factory, required Widget child})`, `OpaqueSurfaceFactory`, `LiquidGlassSurfaceFactory`, `Future<void> initializeGlass()`, `Widget wrapWithGlass(Widget app)`
  - `Pressable({required Widget child, required VoidCallback? onPressed, String? semanticLabel, double minSize = 44})`
  - 테스트 지원: `goldenFrame(Widget child, {Size size})` — 테마·불투명 글래스·그라데이션 바탕을 씌운 고정 크기 틀

계획을 쓰기 전에 확인한 사실
- **테스트에서 `LiquidGlassWidgets.initialize()` 를 부르면 반드시 던진다**(`Asset 'shaders/liquid_glass_render.frag' not found`). 테스트는 `initializeGlass()` 를 부르지 않는다. `GlassContainer` 자체는 테스트에서 예외 없이 그려진다.
- `GlassContainer` 는 주변에 글래스 레이어 조상이 없으면 `useOwnLayer: true` 가 필요하다.
- **Flutter 3.44 에는 iOS "투명도 줄이기"를 알려 주는 신호가 없다**(`AccessibilityFeatures`·`MediaQuery` 에 없음). 패키지의 `GlassAccessibilityData.of(context).reduceTransparency` 는 고대비 설정으로 근사한다. 우리는 그 판정을 그대로 쓴다 — 결정 기록 004 에 한계로 적는다(Task 17).
- `flutter test` 는 글꼴을 싣지 않는다. 글자는 Ahem(네모), **아이콘도 빈 네모**로 찍힌다. `test/flutter_test_config.dart` 가 세 글꼴과 `MaterialIcons` 를 한 번 등록한다(`TestWidgetsFlutterBinding.ensureInitialized()` 가 맨 앞에 있어야 `rootBundle` 을 읽을 수 있다).
- 누르는 효과의 함정 둘: `onTapCancel` 은 위젯이 dispose 되는 중에도 불린다(`mounted` 로도 못 막는다 — `didChangeDependencies` 에서 값을 잡아 둔다). 테스트에서 크기를 읽을 때 `Matrix4.getMaxScaleOnAxis()` 는 z축(항상 1.0)을 잡으므로 `transform.storage[0]` 을 읽는다.
- `pubspec.yaml` 의 `fonts:` 에 선언한 글꼴을 `assets:` 에도 적으면 앱에 **두 번** 들어간다(약 10MB). `assets:` 에는 적지 않는다.

- [ ] **Step 1: 글꼴을 받는다 (셋 다 SIL OFL 1.1)**

Run (`app/` 에서):
```bash
mkdir -p assets/fonts/LICENSES && cd assets/fonts
TMP=$(mktemp -d)
# Bodoni Moda (가변)
curl -fsSL -o BodoniModa-VariableFont.ttf "https://raw.githubusercontent.com/google/fonts/main/ofl/bodonimoda/BodoniModa%5Bopsz%2Cwght%5D.ttf"
curl -fsSL -o LICENSES/BodoniModa-OFL.txt "https://raw.githubusercontent.com/google/fonts/main/ofl/bodonimoda/OFL.txt"
# Pretendard (가변)
curl -fsSL -o "$TMP/pretendard.zip" "https://github.com/orioncactus/pretendard/releases/download/v1.3.9/Pretendard-1.3.9.zip"
unzip -q -o "$TMP/pretendard.zip" -d "$TMP/pretendard"
cp "$TMP/pretendard/public/variable/PretendardVariable.ttf" .
cp "$TMP/pretendard/LICENSE.txt" LICENSES/Pretendard-OFL.txt
# 마루 부리 (zip 안에 MaruBuriTTF.zip 이 또 들어 있다)
curl -fsSL -o "$TMP/maruburi.zip" "https://hangeul.naver.com/hangeul_static/webfont/zips/maruburi.zip"
unzip -q -o "$TMP/maruburi.zip" -d "$TMP/maruburi"
find "$TMP/maruburi" -name "MaruBuriTTF.zip" -exec unzip -q -o {} -d "$TMP/maruburi/ttf" \;
find "$TMP/maruburi/ttf" -name "MaruBuri-Regular.ttf" -exec cp {} . \;
ls -la *.ttf
```
Expected: 세 파일 — `BodoniModa-VariableFont.ttf`(약 160KB), `PretendardVariable.ttf`(약 6.7MB), `MaruBuri-Regular.ttf`(약 3.3MB). 받은 zip 의 폴더 구조가 다르면 `find "$TMP" -name "*.ttf"` 로 찾아 같은 이름으로 복사한다. 네트워크가 막혀 있으면 BLOCKED 로 보고한다.

`assets/fonts/LICENSES/MaruBuri-OFL.txt` 는 네이버의 "나눔글꼴 라이선스 안내"(help.naver.com)에 있는 라이선스 전문을 옮겨 적는다 — `Reserved Font Name MaruBuri`, `licensed under the SIL Open Font License, Version 1.1` 문장이 들어 있어야 한다. 받은 zip 안에 라이선스 파일이 있으면 그것을 쓴다.

`app/pubspec.yaml` 의 `flutter:` 블록:
```yaml
flutter:
  uses-material-design: true
  fonts:
    - family: Pretendard
      fonts:
        - asset: assets/fonts/PretendardVariable.ttf
    - family: BodoniModa
      fonts:
        - asset: assets/fonts/BodoniModa-VariableFont.ttf
    - family: MaruBuri
      fonts:
        - asset: assets/fonts/MaruBuri-Regular.ttf
```

- [ ] **Step 2: 테스트 지원과 실패하는 테스트를 쓴다**

`app/test/flutter_test_config.dart`:
```dart
import 'dart:async';

import 'package:flutter_test/flutter_test.dart';

import 'support/load_fonts.dart';

/// `flutter test`가 이 디렉터리 아래 모든 테스트 파일보다 먼저 실행하는
/// 특수 진입점. 여기서 한 번만 폰트를 로드해두면 개별 테스트 파일에서
/// 매번 `setUpAll(loadTestFonts)`를 쓸 필요가 없다.
Future<void> testExecutable(FutureOr<void> Function() testMain) async {
  // MaterialIcons 폰트를 rootBundle로 읽으려면(load_fonts.dart 참고) 바인딩이
  // 먼저 떠 있어야 한다 — 커스텀 TTF는 dart:io File로 직접 읽어서 필요
  // 없지만, 에셋 번들 조회는 ServicesBinding.instance가 필요하다.
  TestWidgetsFlutterBinding.ensureInitialized();
  await loadTestFonts();
  await testMain();
}
```

`app/test/support/load_fonts.dart`:
```dart
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';

/// 골든 테스트가 "Ahem" 대체 폰트 대신 실제 글꼴 글리프로 렌더링하도록,
/// 번들된 TTF 파일들을 한 번만 로드해 등록한다.
///
/// `flutter test`는 기본적으로 실제 폰트를 로드하지 않고 테스트용
/// Ahem 폰트(글자마다 사각형 박스)를 쓴다. 골든에 진짜 글리프가
/// 보이도록 하려면 [FontLoader]로 TTF를 직접 등록해야 한다.
///
/// [test/flutter_test_config.dart]의 `testExecutable`에서 모든 테스트가
/// 시작되기 전에 딱 한 번 호출한다.
Future<void> loadTestFonts() async {
  await _loadFont('Pretendard', 'assets/fonts/PretendardVariable.ttf');
  await _loadFont('BodoniModa', 'assets/fonts/BodoniModa-VariableFont.ttf');
  await _loadFont('MaruBuri', 'assets/fonts/MaruBuri-Regular.ttf');
  await _loadMaterialIconsFont();
}

Future<void> _loadFont(String family, String path) async {
  final file = File(path);
  if (!file.existsSync()) {
    // 폰트 파일이 없어도 테스트 스위트 전체가 죽지 않게 한다 — 대신 그
    // 폰트를 쓰는 골든은 Ahem으로 실패해 원인을 바로 알 수 있다.
    debugPrint('[loadTestFonts] 폰트 파일을 찾을 수 없음: $path');
    return;
  }
  final bytes = await file.readAsBytes();
  final loader = FontLoader(family)
    ..addFont(Future.value(ByteData.view(bytes.buffer)));
  await loader.load();
}

/// `Icon(Icons.xxx)`는 "MaterialIcons"라는 폰트의 글리프다. `uses-material-
/// design: true`면 Flutter 툴이 엔진 캐시의 `MaterialIcons-Regular.otf`를
/// 자동으로 앱 폰트 매니페스트(`fonts/MaterialIcons-Regular.otf`)에 넣어
/// 주지만, `flutter test`는 이걸 자동으로 로드하지 않는다(커스텀 폰트와
/// 같은 이유) — 안 불러오면 골든에 아이콘이 빈 사각형(tofu)으로 찍힌다.
/// SDK 캐시 경로를 직접 하드코딩하지 않고, 이미 번들된 에셋 키를
/// `rootBundle`로 읽어서 그대로 등록한다.
Future<void> _loadMaterialIconsFont() async {
  try {
    final data = await rootBundle.load('fonts/MaterialIcons-Regular.otf');
    final loader = FontLoader('MaterialIcons')..addFont(Future.value(data));
    await loader.load();
  } catch (e) {
    debugPrint('[loadTestFonts] MaterialIcons 폰트를 불러오지 못함: $e');
  }
}
```

`app/test/support/golden_frame.dart`:
```dart
import 'package:chagocnote/design/app_theme.dart';
import 'package:chagocnote/design/bridge/glass_surface.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

/// 골든 테스트용 고정 프레임.
///
/// `MaterialApp(theme: appTheme())` + `GlassBridge(factory:
/// OpaqueSurfaceFactory())` + 배경 그라데이션(`AppBackground`)으로
/// 위젯을 감싸고, 표면 크기와 devicePixelRatio를 고정해 골든이 기기·환경마다
/// 달라지지 않게 한다. 유리 위젯은 항상 불투명 대체 표면으로 찍힌다 —
/// 스펙이 요구하는 "투명도 줄이기" 골든과 같은 모습이다.
///
/// `child`를 `RepaintBoundary`로 감싸서 반환한 [Finder]로
/// `matchesGoldenFile`을 찍으면, 화면 전체가 아니라 그 위젯 크기만큼만
/// 잘려서 찍힌다.
Future<Finder> pumpGoldenFrame(
  WidgetTester tester,
  Widget child, {
  Size surfaceSize = const Size(390, 500),
}) async {
  tester.view.physicalSize = surfaceSize;
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);

  final key = GlobalKey();

  await tester.pumpWidget(
    MaterialApp(
      theme: appTheme(),
      debugShowCheckedModeBanner: false,
      home: GlassBridge(
        factory: const OpaqueSurfaceFactory(),
        child: AppBackground(
          child: Scaffold(
            backgroundColor: Colors.transparent,
            body: Center(child: RepaintBoundary(key: key, child: child)),
          ),
        ),
      ),
    ),
  );

  return find.byKey(key);
}
```

`app/test/design/glass_surface_test.dart`:
```dart
import 'package:chagocnote/design/bridge/glass_surface.dart';
import 'package:flutter/cupertino.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:liquid_glass_widgets/liquid_glass_widgets.dart';

void main() {
  testWidgets('투명도 줄이기가 켜지면 GlassSurface는 불투명 표면을 쓴다', (tester) async {
    await tester.pumpWidget(
      const CupertinoApp(
        home: GlassAccessibilityScope(
          reduceTransparency: true,
          child: Center(child: GlassSurface(child: Text('안녕'))),
        ),
      ),
    );
    await tester.pump();

    expect(find.byType(GlassContainer), findsNothing);
    expect(find.text('안녕'), findsOneWidget);
  });

  testWidgets('투명도 줄이기가 꺼져 있으면 GlassSurface는 실제 GlassContainer를 쓴다', (
    tester,
  ) async {
    await tester.pumpWidget(
      const CupertinoApp(home: Center(child: GlassSurface(child: Text('안녕')))),
    );
    await tester.pump();

    expect(find.byType(GlassContainer), findsOneWidget);
  });

  testWidgets('GlassBridge로 감싸면 그 팩토리를 쓴다', (tester) async {
    await tester.pumpWidget(
      const CupertinoApp(
        home: GlassBridge(
          factory: OpaqueSurfaceFactory(),
          child: Center(child: GlassSurface(child: Text('안녕'))),
        ),
      ),
    );
    await tester.pump();

    expect(find.byType(GlassContainer), findsNothing);
  });
}
```

`app/test/design/pressable_test.dart`:
```dart
import 'package:chagocnote/design/widgets/pressable.dart';
import 'package:flutter/cupertino.dart';
import 'package:flutter_test/flutter_test.dart';

// Transform.scale은 x/y만 스케일하고 z축은 그대로 둔다. 그래서
// `Matrix4.getMaxScaleOnAxis()`는 z축의 1.0을 최댓값으로 잡아 항상 1.0을
// 반환한다 — 실제 2D 스케일 값은 행렬의 (0,0) 성분을 직접 읽어야 한다.
double _readScaleX(WidgetTester tester) =>
    tester.widget<Transform>(find.byType(Transform)).transform.storage[0];

Opacity _findOpacity(WidgetTester tester) =>
    tester.widget<Opacity>(find.byType(Opacity));

void main() {
  testWidgets('누르는 중간에는 스케일이 1보다 작아진다', (tester) async {
    await tester.pumpWidget(
      CupertinoApp(
        home: Center(child: Pressable(onTap: () {}, child: const Text('버튼'))),
      ),
    );

    final center = tester.getCenter(find.text('버튼'));
    final gesture = await tester.startGesture(center);
    // TapGestureRecognizer는 onTapDown을 kPressTimeout(100ms) 뒤에야
    // 부르므로, 그 뒤로 스프링이 진행 중인 중간 지점까지 pump한다.
    await tester.pump(const Duration(milliseconds: 100));
    await tester.pump(const Duration(milliseconds: 40));

    final scale = _readScaleX(tester);
    expect(scale, lessThan(1.0));
    expect(scale, greaterThanOrEqualTo(0.9));

    await gesture.up();
    await tester.pumpAndSettle();

    final settledScale = _readScaleX(tester);
    expect(settledScale, closeTo(1.0, 0.001));
  });

  testWidgets('disableAnimations가 true면 예외 없이 페이드로 대체한다', (tester) async {
    await tester.pumpWidget(
      MediaQuery(
        data: const MediaQueryData(
          accessibleNavigation: false,
          disableAnimations: true,
        ),
        child: CupertinoApp(
          home: Center(
            child: Pressable(onTap: () {}, child: const Text('버튼')),
          ),
        ),
      ),
    );

    final center = tester.getCenter(find.text('버튼'));
    final gesture = await tester.startGesture(center);
    await tester.pump(const Duration(milliseconds: 100));
    await tester.pump(const Duration(milliseconds: 40));

    // 스케일 트랜스폼 대신 Opacity가 쓰인다 — Transform 자체가 트리에 없다.
    expect(_findOpacity(tester).opacity, lessThan(1.0));
    expect(find.byType(Transform), findsNothing);

    await gesture.up();
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
  });

  testWidgets('탭 영역은 시각적 크기가 작아도 최소 44x44를 확보한다', (tester) async {
    await tester.pumpWidget(
      CupertinoApp(
        home: Center(
          child: Pressable(onTap: () {}, child: const Text('X')),
        ),
      ),
    );

    final size = tester.getSize(find.byType(Pressable));
    expect(size.width, greaterThanOrEqualTo(44));
    expect(size.height, greaterThanOrEqualTo(44));
  });
}
```

`app/test/design/import_boundary_test.dart`:
```dart
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

/// `liquid_glass_widgets`는 `lib/design/bridge/` 안에서만 import할 수
/// 있다 — 화면 코드가 실제 유리 렌더러를 직접 알면 안 된다는 경계를
/// grep으로 강제한다.
void main() {
  test('liquid_glass_widgets는 lib/design/bridge/ 밖에서 import되지 않는다', () {
    final libDir = Directory('lib');
    final violations = <String>[];

    for (final entity in libDir.listSync(recursive: true)) {
      if (entity is! File || !entity.path.endsWith('.dart')) continue;

      final normalized = entity.path.replaceAll(r'\', '/');
      if (normalized.contains('lib/design/bridge/')) continue;

      final content = entity.readAsStringSync();
      if (content.contains('package:liquid_glass_widgets')) {
        violations.add(normalized);
      }
    }

    expect(
      violations,
      isEmpty,
      reason: 'lib/design/bridge/ 밖에서 liquid_glass_widgets를 import함: $violations',
    );
  });
}
```

Run: `flutter test test/design`
Expected: FAIL — `Not found: 'package:chagocnote/design/…'`

- [ ] **Step 3: 토큰과 테마**

`app/lib/design/tokens/app_colors.dart`:
```dart
import 'package:flutter/widgets.dart';

/// 차곡노트 디자인 톤 — 무채색 회백 배경에 검정 한 가지 포인트.
///
/// 색은 사진에서만 온다. 이 팔레트 밖의 색을 새로 들이지 않는다.
abstract final class AppColors {
  /// 배경 그라데이션 시작(위쪽).
  static const backgroundTop = Color(0xFFF5F5F5);

  /// 배경 그라데이션 끝(아래쪽).
  static const backgroundBottom = Color(0xFFECECEC);

  /// 본문 텍스트·아이콘·단일 포인트 색.
  static const ink = Color(0xFF161616);

  /// 보조 텍스트(캡션, 비활성 상태).
  static const secondary = Color(0xFF8D8D8D);

  /// 구분선.
  static const line = Color(0xFFDCDCDC);

  /// 사진 테두리·글래스 채움·FAB 아이콘에만 쓰는 흰색.
  static const white = Color(0xFFFFFFFF);

  /// 배경에 쓰는 세로 방향 그라데이션.
  static const backgroundGradient = LinearGradient(
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
    colors: [backgroundTop, backgroundBottom],
  );
}
```

`app/lib/design/tokens/app_typography.dart`:
```dart
import 'package:flutter/widgets.dart';

import 'app_colors.dart';

/// 텍스트 스타일 프리셋.
///
/// 본문은 Pretendard, 큰 숫자와 영문 타이틀은 Bodoni Moda(고대비 세리프),
/// 한글 타이틀은 MaruBuri를 쓴다.
abstract final class AppTypography {
  static const _pretendard = 'Pretendard';
  static const _bodoniModa = 'BodoniModa';
  static const _maruBuri = 'MaruBuri';

  /// 기본 본문.
  static const body = TextStyle(
    fontFamily: _pretendard,
    fontSize: 14,
    height: 1.4,
    fontWeight: FontWeight.w400,
    color: AppColors.ink,
  );

  /// 강조 본문(버튼 라벨 등).
  static const bodyStrong = TextStyle(
    fontFamily: _pretendard,
    fontSize: 14,
    height: 1.4,
    fontWeight: FontWeight.w600,
    color: AppColors.ink,
  );

  /// 작은 보조 텍스트.
  static const caption = TextStyle(
    fontFamily: _pretendard,
    fontSize: 11,
    height: 1.3,
    fontWeight: FontWeight.w500,
    color: AppColors.secondary,
  );

  /// 한글 타이틀("오늘의 케어" 같은 섹션 제목).
  static const titleKo = TextStyle(
    fontFamily: _maruBuri,
    fontSize: 19,
    height: 1.25,
    fontWeight: FontWeight.w400,
    color: AppColors.ink,
  );

  /// 영문 타이틀("care diary", "Daily record" 같은 브랜드/화면 제목).
  static const titleEn = TextStyle(
    fontFamily: _bodoniModa,
    fontSize: 16,
    height: 1.1,
    fontWeight: FontWeight.w500,
    color: AppColors.ink,
  );

  /// 날짜 숫자처럼 아주 큰 세리프 숫자. 줄 높이를 바짝 붙인다.
  static const bigNumeral = TextStyle(
    fontFamily: _bodoniModa,
    fontSize: 82,
    height: 0.84,
    letterSpacing: -4,
    fontWeight: FontWeight.w400,
    color: AppColors.ink,
  );

  /// 영문 월·요일처럼 기울인 세리프 라벨.
  static const italicLabel = TextStyle(
    fontFamily: _bodoniModa,
    fontSize: 30,
    height: 0.95,
    fontStyle: FontStyle.italic,
    fontWeight: FontWeight.w400,
    color: AppColors.ink,
  );
}
```

`app/lib/design/tokens/app_spacing.dart`:
```dart
/// 4pt 간격 스케일.
abstract final class AppSpacing {
  static const double xs = 4;
  static const double sm = 8;
  static const double md = 12;
  static const double lg = 16;
  static const double xl = 24;
  static const double xxl = 32;
}
```

`app/lib/design/tokens/app_radius.dart`:
```dart
/// 모서리 반지름 스케일. `pill`은 알약 모양(높이의 절반 이상)에 쓴다.
abstract final class AppRadius {
  static const double sm = 8;
  static const double md = 12;
  static const double lg = 16;
  static const double xl = 24;
  static const double pill = 999;
}
```

`app/lib/design/tokens/app_shadows.dart`:
```dart
import 'package:flutter/widgets.dart';

/// 그림자 프리셋. 무채색 배경에서 색이 아니라 깊이로만 위계를 준다.
abstract final class AppShadows {
  /// 카드·타일처럼 배경에 살짝 얹힌 요소.
  static const soft = [
    BoxShadow(color: Color(0x14000000), blurRadius: 12, offset: Offset(0, 4)),
  ];

  /// 탭바·FAB·시트처럼 떠 있는 컨트롤 레이어.
  static const floating = [
    BoxShadow(color: Color(0x33000000), blurRadius: 20, offset: Offset(0, 8)),
  ];
}
```

`app/lib/design/tokens/app_springs.dart`:
```dart
import 'package:flutter/physics.dart';

/// 스프링 물리 프리셋. 고정 커브 대신 스프링으로 눌림/복귀를 표현한다.
abstract final class AppSprings {
  /// 누르는 순간(스케일이 줄어드는 쪽) — 빠르고 절제된 반응.
  static final press = SpringDescription.withDampingRatio(
    mass: 1,
    stiffness: 500,
    ratio: 0.6,
  );

  /// 손을 뗐을 때 원래 크기로 되돌아오는 쪽 — 살짝 더 튀는 느낌을 준다.
  static final settle = SpringDescription.withDampingRatio(
    mass: 1,
    stiffness: 300,
    ratio: 0.5,
  );

  /// "동작 줄이기"가 켜졌을 때 스프링 대신 쓰는 페이드 지속 시간.
  static const fadeDuration = Duration(milliseconds: 80);
}
```

`app/lib/design/app_theme.dart`:
```dart
import 'package:flutter/material.dart';

import 'tokens/app_colors.dart';

/// Material 3 기반 앱 테마. 무채색 톤이라 시드에서 나온 색조가 새 색을
/// 들이지 않도록 주요 역할(primary/secondary/surface/error)을 직접
/// ink/white/backgroundTop으로 덮어쓴다.
ThemeData appTheme() {
  final colorScheme = ColorScheme.fromSeed(
    seedColor: AppColors.ink,
  ).copyWith(
    primary: AppColors.ink,
    onPrimary: AppColors.white,
    secondary: AppColors.ink,
    onSecondary: AppColors.white,
    surface: AppColors.backgroundTop,
    onSurface: AppColors.ink,
    error: AppColors.ink,
    onError: AppColors.white,
  );

  return ThemeData(
    useMaterial3: true,
    colorScheme: colorScheme,
    fontFamily: 'Pretendard',
    // 배경 그라데이션은 AppBackground가 그리므로 스캐폴드 자체는 투명하게
    // 비워둔다.
    scaffoldBackgroundColor: Colors.transparent,
    // Pressable이 스케일+햅틱으로 자체 눌림 피드백을 주므로, Material
    // 기본 잉크 리플/하이라이트는 새 색조를 들이지 않게 꺼둔다.
    splashFactory: NoSplash.splashFactory,
    splashColor: Colors.transparent,
    highlightColor: Colors.transparent,
    hoverColor: Colors.transparent,
    focusColor: Colors.transparent,
    textTheme: Typography.blackMountainView.apply(
      fontFamily: 'Pretendard',
      bodyColor: AppColors.ink,
      displayColor: AppColors.ink,
    ),
  );
}

/// 화면 배경에 세로 그라데이션(`#f5f5f5` → `#ececec`)을 깔아주는 위젯.
///
/// `Scaffold`는 투명 배경으로 두고, 이 위젯으로 감싸서 그 뒤에 그라데이션이
/// 보이게 한다.
class AppBackground extends StatelessWidget {
  const AppBackground({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: const BoxDecoration(gradient: AppColors.backgroundGradient),
      child: child,
    );
  }
}
```

- [ ] **Step 4: 글래스 브리지와 누르는 효과**

`app/lib/design/bridge/glass_surface.dart`:
```dart
import 'package:flutter/cupertino.dart';
import 'package:liquid_glass_widgets/liquid_glass_widgets.dart';

/// 유리(glass) 표면을 실제로 그리는 방법을 감춘 추상 팩토리.
///
/// 구현체를 바꿔치기하면 실제 리퀴드 글래스 렌더러(`GlassContainer`)와
/// 완전 불투명 대체 표면(`OpaqueSurfaceFactory`)을 동일한 인터페이스로
/// 다룰 수 있다.
abstract class GlassSurfaceFactory {
  Widget build({
    required Widget child,
    required BorderRadius borderRadius,
    EdgeInsetsGeometry? padding,
  });
}

/// `liquid_glass_widgets`의 [GlassContainer]로 실제 유리 효과를 그린다.
///
/// `useOwnLayer: true`를 써서 주변에 [LiquidGlassLayer] 조상이 없어도
/// 어디서든 단독으로 쓸 수 있게 한다 (README의 "Standalone Mode").
class LiquidGlassSurfaceFactory implements GlassSurfaceFactory {
  const LiquidGlassSurfaceFactory();

  @override
  Widget build({
    required Widget child,
    required BorderRadius borderRadius,
    EdgeInsetsGeometry? padding,
  }) {
    // LiquidRoundedRectangle은 모서리 반지름을 double 하나로 받는다(대칭 모양
    // 전용). 카드류는 보통 네 모서리가 같으므로 topLeft 값을 대표로 쓴다.
    return GlassContainer(
      useOwnLayer: true,
      shape: LiquidRoundedRectangle(borderRadius: borderRadius.topLeft.x),
      padding: padding,
      child: child,
    );
  }
}

/// 그림자 없는 완전 불투명 대체 표면.
///
/// 흰색 92% 불투명 채움 + 1px `#dcdcdc` 테두리 + 은은한 그림자로,
/// 셰이더도 `BackdropFilter`도 전혀 쓰지 않는다. 테스트 환경, 저사양
/// 기기, "투명도 줄이기"가 켜진 경우의 대체 표면으로 쓴다.
class OpaqueSurfaceFactory implements GlassSurfaceFactory {
  const OpaqueSurfaceFactory();

  static const _fill = Color.fromRGBO(255, 255, 255, 0.92);
  static const _border = Color(0xFFDCDCDC);

  @override
  Widget build({
    required Widget child,
    required BorderRadius borderRadius,
    EdgeInsetsGeometry? padding,
  }) {
    return Container(
      padding: padding,
      decoration: BoxDecoration(
        color: _fill,
        borderRadius: borderRadius,
        border: Border.all(color: _border, width: 1),
        boxShadow: const [
          BoxShadow(
            color: Color(0x14000000),
            blurRadius: 12,
            offset: Offset(0, 4),
          ),
        ],
      ),
      child: child,
    );
  }
}

/// 상위 트리에 유리 표면 팩토리를 제공하는 [InheritedWidget].
///
/// 화면/기능 단위에서 실제 렌더러를 바꿔 끼우고 싶을 때(예: 데모 화면에서
/// 강제로 불투명 표면만 보여주기) 이 위젯으로 감싸면 된다. 감싸지 않으면
/// [GlassSurface]가 기본값으로 [LiquidGlassSurfaceFactory]를 쓴다.
class GlassBridge extends InheritedWidget {
  const GlassBridge({
    super.key,
    required this.factory,
    required super.child,
  });

  final GlassSurfaceFactory factory;

  static GlassSurfaceFactory of(BuildContext context) {
    final bridge = context.dependOnInheritedWidgetOfExactType<GlassBridge>();
    return bridge?.factory ?? const LiquidGlassSurfaceFactory();
  }

  @override
  bool updateShouldNotify(GlassBridge oldWidget) =>
      factory != oldWidget.factory;
}

/// 유리 표면 하나를 그리는 위젯.
///
/// "투명도 줄이기"를 존중해야 하는 상황이면(시스템 설정, 명시적
/// [GlassAccessibilityScope] 오버라이드, 혹은 테스트에서 강제로 켠 경우)
/// [OpaqueSurfaceFactory]로 대체하고, 그렇지 않으면 [GlassBridge]가
/// 제공한 팩토리(기본은 실제 리퀴드 글래스)를 그대로 쓴다.
///
/// 판정 기준은 `liquid_glass_widgets`가 이미 갖고 있는
/// [GlassAccessibilityData.of]를 그대로 재사용한다 — 우선순위는
/// (1) 트리 안의 명시적 [GlassAccessibilityScope],
/// (2) 시스템 `MediaQuery.highContrastOf` (iOS "투명도 줄이기"에 대한
/// Flutter의 근사치 — 정확히 일치하는 신호는 없다),
/// (3) `LiquidGlassWidgets.wrap(respectSystemAccessibility: false)`로
/// 전역 비활성화한 경우의 기본값(false) 순이다.
class GlassSurface extends StatelessWidget {
  const GlassSurface({
    super.key,
    required this.child,
    this.borderRadius = const BorderRadius.all(Radius.circular(16)),
    this.padding,
  });

  final Widget child;
  final BorderRadius borderRadius;
  final EdgeInsetsGeometry? padding;

  @override
  Widget build(BuildContext context) {
    final reduceTransparency =
        GlassAccessibilityData.of(context).reduceTransparency;
    final factory = reduceTransparency
        ? const OpaqueSurfaceFactory()
        : GlassBridge.of(context);
    return factory.build(
      child: child,
      borderRadius: borderRadius,
      padding: padding,
    );
  }
}
```

`app/lib/design/bridge/glass_setup.dart`:
```dart
import 'package:flutter/widgets.dart';
import 'package:liquid_glass_widgets/liquid_glass_widgets.dart';

// `liquid_glass_widgets`를 앱 진입점에서 초기화하고 감싸는 두 함수.
//
// `main.dart`가 패키지를 직접 import하지 않도록, 셋업 관련 호출은
// 전부 이 파일 뒤에 감춘다(다른 브리지 파일과 같은 원칙).

/// 셰이더를 미리 디스크에서 RAM으로 올려 첫 프레임 깜빡임을 없앤다.
///
/// 스파이크(Q1)에서 확인한 대로 필수는 아니지만 권장된다. **테스트에서는
/// 절대 호출하면 안 된다** — 테스트 환경에는 셰이더 에셋이 없어서 예외를
/// 던진다(FINDINGS.md Q2-1 참고).
Future<void> initializeGlass() => LiquidGlassWidgets.initialize();

/// 앱 루트를 유리 인프라 스코프로 감싼다.
///
/// `adaptiveQuality: true`를 켠다 — 기기를 실시간으로 벤치마크해서 유리
/// 품질 상한을 조정한다(1단계: 셰이더 미지원 기기는 즉시 `minimal`로 고정,
/// 2단계: 첫 ~3초간 실제 래스터 시간을 측정해 초기 품질을 정함, 3단계:
/// 이후 지속적으로 프레임 예산을 넘기면 품질을 낮추고 여유가 생기면
/// 다시 올림). 저사양 안드로이드에서 셰이더 품질을 자동으로 낮춰 프레임
/// 드랍을 줄이는 게 목적이다 — 패키지 문서상 0.8.0 기준 "실험적" 기능이라
/// 임계값이 전체 안드로이드 기기군에서 검증되진 않았다고 명시돼 있다.
Widget wrapWithGlass(Widget app) {
  return LiquidGlassWidgets.wrap(child: app, adaptiveQuality: true);
}
```

`app/lib/design/widgets/pressable.dart`:
```dart
import 'package:flutter/cupertino.dart';
import 'package:flutter/physics.dart';
import 'package:flutter/services.dart';

import '../tokens/app_springs.dart';

/// 누르면 0.96배로 눌렸다가 스프링으로 되돌아오는 "누를 수 있는" 래퍼.
///
/// - 누르는 순간 가벼운 햅틱을 준다.
/// - `MediaQuery.disableAnimationsOf`가 true(시스템 "동작 줄이기")이면
///   스프링 스케일 대신 옅은 페이드로 대체한다.
/// - `semanticLabel`을 주면 버튼으로 접근성에 노출한다.
/// - 시각적 크기가 44×44보다 작아도 탭 영역은 `minSize`(기본 44) 이상을
///   보장한다.
class Pressable extends StatefulWidget {
  const Pressable({
    super.key,
    required this.child,
    this.onTap,
    this.semanticLabel,
    this.minSize = 44,
  });

  final Widget child;
  final VoidCallback? onTap;
  final String? semanticLabel;
  final double minSize;

  @override
  State<Pressable> createState() => _PressableState();
}

class _PressableState extends State<Pressable>
    with SingleTickerProviderStateMixin {
  static const double _pressedScale = 0.96;
  static const double _pressedOpacity = 0.6;

  late final AnimationController _controller = AnimationController(
    vsync: this,
    value: 0, // 0 = 안 눌림, 1 = 완전히 눌림
  );

  // didChangeDependencies에서 미리 읽어 캐시해둔다. onTapCancel은 위젯이
  // 통째로 해제되는 도중(자식 GestureDetector의 dispose 연쇄)에도 불릴 수
  // 있는데, 그 시점엔 이 State의 context가 이미 "inactive"라 MediaQuery를
  // 다시 조회하면 "Looking up a deactivated widget's ancestor" 단언에
  // 걸린다 — mounted 체크만으론 못 막는다(inactive여도 mounted는 true).
  late bool _reduceMotion;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _reduceMotion = MediaQuery.disableAnimationsOf(context);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _animateTo(double target) {
    if (_reduceMotion) {
      // 동작 줄이기: 스프링 없이 짧은 페이드만.
      _controller.animateTo(target, duration: AppSprings.fadeDuration);
    } else {
      // 누를 때와 뗄 때 서로 다른 스프링을 써서 "눌림"과 "복귀"의 질감을
      // 다르게 준다 — 복귀 쪽이 조금 더 튀는 느낌.
      final spring = target == 1 ? AppSprings.press : AppSprings.settle;
      final simulation = SpringSimulation(spring, _controller.value, target, 0);
      _controller.animateWith(simulation);
    }
  }

  void _onTapDown(TapDownDetails _) {
    HapticFeedback.lightImpact();
    _animateTo(1);
  }

  void _onTapEnd([TapUpDetails? _]) {
    _animateTo(0);
  }

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: widget.onTap != null,
      label: widget.semanticLabel,
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: widget.onTap,
        onTapDown: _onTapDown,
        onTapUp: _onTapEnd,
        onTapCancel: _onTapEnd,
        // Center를 쓰지 않는다 — Row 안에서 flex가 아닌 자식(예: AppSegment의
        // 탭)은 주축으로 무한대(loose, maxWidth: infinity) 제약을 받는데,
        // Center/Align은 factor가 없으면 "가능한 한 크게" 채우려다 그
        // 무한대를 그대로 자기 크기로 쓰려 해서 런타임에 깨진다. 대신
        // ConstrainedBox 하나만 써서 자식이 원래 크기보다 작을 때만
        // 최소 44×44까지 조용히 채워지게 한다.
        child: ConstrainedBox(
          constraints: BoxConstraints(
            minWidth: widget.minSize,
            minHeight: widget.minSize,
          ),
          child: AnimatedBuilder(
            animation: _controller,
            builder: (context, child) {
              final t = _controller.value.clamp(0.0, 1.0);
              if (_reduceMotion) {
                return Opacity(
                  opacity: 1 - t * (1 - _pressedOpacity),
                  child: child,
                );
              }
              final scale = 1 - t * (1 - _pressedScale);
              return Transform.scale(scale: scale, child: child);
            },
            child: widget.child,
          ),
        ),
      ),
    );
  }
}
```

- [ ] **Step 5: 통과를 확인한다**

Run: `flutter test test/design && flutter analyze`
Expected: `All tests passed!` (7개), `No issues found!`

- [ ] **Step 6: 커밋**

```bash
git add app/assets app/pubspec.yaml app/lib/design app/test/flutter_test_config.dart app/test/support app/test/design
git commit -m "feat(app): 디자인 기반 — 글꼴 3종, 토큰, 테마, 글래스 브리지, 누르는 효과"
```

### Task 3: 기본 위젯 9개와 골든 테스트

**Files:**
- Create: `app/lib/design/widgets/{app_button,app_fab,app_glass_bar,app_glass_card,app_sheet,app_segment,app_photo_tile,app_big_date,app_chip}.dart`
- Test: `app/test/design/{app_button,app_glass_bar,app_segment,app_photo_tile,app_big_date}_test.dart`, `app/test/design/app_*_golden_test.dart` 9개, `app/test/design/goldens/*.png` 9개(생성물)

**Interfaces:**
- Consumes: Task 2 의 토큰·`appTheme`·`GlassSurface`·`Pressable`·`goldenFrame`
- Produces (화면 작업이 쓰는 API — 시그니처를 바꾸지 않는다):
  - `AppButton({required String label, required VoidCallback? onPressed, bool filled = false, bool busy = false, IconData? icon})`
  - `AppFab({required VoidCallback onPressed, IconData icon = Icons.add, String? semanticLabel})`
  - `AppGlassBar({required List<AppGlassBarItem> items, required int currentIndex, required ValueChanged<int> onTap})`, `AppGlassBarItem({required IconData icon, required String label})`
  - `AppGlassCard({required Widget child, EdgeInsetsGeometry padding})`
  - `AppSheet.show<T>(BuildContext context, {required WidgetBuilder builder}) → Future<T?>`
  - `AppSegment({required List<String> labels, required int currentIndex, required ValueChanged<int> onChanged})`
  - `AppPhotoTile({required ImageProvider? image, int? count, double size = 72})`
  - `AppBigDate({required DateTime date})`
  - `AppChip({required String label})`

규칙
- 색은 `AppColors` 의 여섯 값만 쓴다. 새 색을 만들지 않는다. 글래스는 `AppGlassBar`·`AppGlassCard`·`AppSheet` 에만 쓴다.
- 누를 수 있는 위젯은 전부 `Pressable` 을 쓰고, 의미 라벨이 있고, 터치 영역이 44×44 이상이다.
- 골든은 **불투명 대체 면**으로 찍는다(`goldenFrame` 이 `GlassBridge(factory: OpaqueSurfaceFactory())` 를 씌운다). 이것이 설계 8.2절이 말한 "투명도 줄이기 대체 모습"이다. 실제 글래스의 굴절은 골든으로 확인할 수 없다 — Task 17 에서 시뮬레이터로 본다.
- 실험에서 걸린 함정: `Row` 안의 고정 폭 자식에 `Center` 를 넣으면 주축 폭이 무한대가 되어 터진다(`AppSegment`). `CircularProgressIndicator` 가 있는 화면은 `pumpAndSettle` 이 끝나지 않는다 — 고정 시간 `pump(duration)` 을 쓴다.

- [ ] **Step 1: 동작 테스트와 골든 테스트를 쓴다**

`app/test/design/app_button_test.dart`:
```dart
import 'package:chagocnote/design/widgets/app_button.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

Future<void> _tap(WidgetTester tester, Finder finder) async {
  final gesture = await tester.startGesture(tester.getCenter(finder));
  await tester.pump(const Duration(milliseconds: 100));
  await gesture.up();
  await tester.pumpAndSettle();
}

// busy 버튼은 CircularProgressIndicator가 계속 회전해서 pumpAndSettle이
// 끝나지 않는다 — 고정된 pump 몇 번으로 대신한다.
Future<void> _tapBusy(WidgetTester tester, Finder finder) async {
  final gesture = await tester.startGesture(tester.getCenter(finder));
  await tester.pump(const Duration(milliseconds: 100));
  await gesture.up();
  await tester.pump(const Duration(milliseconds: 100));
}

void main() {
  testWidgets('활성 버튼을 누르면 onPressed가 호출된다', (tester) async {
    var tapped = false;
    await tester.pumpWidget(
      MaterialApp(
        home: Center(
          child: AppButton(label: '기록 수정', onPressed: () => tapped = true),
        ),
      ),
    );

    await _tap(tester, find.text('기록 수정'));
    expect(tapped, isTrue);
  });

  testWidgets('busy면 스피너를 보여주고 onPressed를 부르지 않는다', (tester) async {
    var tapped = false;
    await tester.pumpWidget(
      MaterialApp(
        home: Center(
          child: AppButton(
            label: '저장',
            onPressed: () => tapped = true,
            busy: true,
          ),
        ),
      ),
    );

    expect(find.byType(CircularProgressIndicator), findsOneWidget);
    await _tapBusy(tester, find.text('저장'));
    expect(tapped, isFalse);
  });

  testWidgets('onPressed가 null이면(비활성) 탭해도 아무 일도 없다', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Center(child: AppButton(label: '저장', onPressed: null)),
      ),
    );

    await _tap(tester, find.text('저장'));
    expect(tester.takeException(), isNull);
  });
}
```

`app/test/design/app_glass_bar_test.dart`:
```dart
import 'package:chagocnote/design/tokens/app_colors.dart';
import 'package:chagocnote/design/widgets/app_glass_bar.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  const items = [
    AppGlassBarItem(icon: Icons.calendar_today, label: '캘린더'),
    AppGlassBarItem(icon: Icons.people_outline, label: '고객'),
    AppGlassBarItem(icon: Icons.bar_chart, label: '매출'),
  ];

  testWidgets('탭하면 해당 인덱스로 onTap이 불린다', (tester) async {
    int? tappedIndex;
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: AppGlassBar(
            items: items,
            currentIndex: 0,
            onTap: (i) => tappedIndex = i,
          ),
        ),
      ),
    );

    final gesture = await tester.startGesture(tester.getCenter(find.text('매출')));
    await tester.pump(const Duration(milliseconds: 100));
    await gesture.up();
    await tester.pumpAndSettle();

    expect(tappedIndex, 2);
  });

  testWidgets('선택된 슬롯은 잉크 색, 나머지는 보조 색이다', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: AppGlassBar(items: items, currentIndex: 1, onTap: (_) {}),
        ),
      ),
    );

    final selectedText = tester.widget<Text>(find.text('고객'));
    final unselectedText = tester.widget<Text>(find.text('캘린더'));

    expect(selectedText.style!.color, AppColors.ink);
    expect(unselectedText.style!.color, AppColors.secondary);
  });
}
```

`app/test/design/app_segment_test.dart`:
```dart
import 'package:chagocnote/design/widgets/app_segment.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('탭을 누르면 그 인덱스로 onChanged가 불린다', (tester) async {
    int? changedIndex;
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: AppSegment(
            labels: const ['캘린더', '기록'],
            currentIndex: 0,
            onChanged: (i) => changedIndex = i,
          ),
        ),
      ),
    );

    final gesture = await tester.startGesture(tester.getCenter(find.text('기록')));
    await tester.pump(const Duration(milliseconds: 100));
    await gesture.up();
    await tester.pumpAndSettle();

    expect(changedIndex, 1);
  });
}
```

`app/test/design/app_photo_tile_test.dart`:
```dart
import 'package:chagocnote/design/widgets/app_photo_tile.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('count를 주면 숫자가 표시된다', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Center(child: AppPhotoTile(image: null, count: 4)),
      ),
    );

    expect(find.text('4'), findsOneWidget);
  });

  testWidgets('count가 없으면 숫자를 표시하지 않는다', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: Center(child: AppPhotoTile(image: null))),
    );

    expect(find.text('4'), findsNothing);
  });
}
```

`app/test/design/app_big_date_test.dart`:
```dart
import 'package:chagocnote/design/widgets/app_big_date.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('2026-09-22는 22, September, Tuesday로 보여준다', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Center(child: AppBigDate(date: DateTime(2026, 9, 22))),
      ),
    );

    expect(find.text('22'), findsOneWidget);
    expect(find.text('September'), findsOneWidget);
    expect(find.text('Tuesday'), findsOneWidget);
  });
}
```

`app/test/design/app_button_golden_test.dart`:
```dart
import 'package:chagocnote/design/widgets/app_button.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../support/golden_frame.dart';

void _noop() {}

void main() {
  testWidgets('AppButton 골든 — 아웃라인 / 채움 / busy / 비활성', (tester) async {
    final target = await pumpGoldenFrame(
      tester,
      Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: const [
          AppButton(label: '기록 수정', onPressed: _noop),
          SizedBox(height: 12),
          AppButton(label: '저장', onPressed: _noop, filled: true),
          SizedBox(height: 12),
          AppButton(label: '저장 중', onPressed: _noop, busy: true),
          SizedBox(height: 12),
          AppButton(label: '저장', onPressed: null),
        ],
      ),
    );

    // busy 버튼의 CircularProgressIndicator는 첫 프레임(t=0)에 호(arc)가
    // 거의 안 보인다. 고정된 시간만큼 더 진행시켜서(항상 같은 위상이라
    // 결정적이다) 스피너가 실제로 보이는 골든을 찍는다.
    await tester.pump(const Duration(milliseconds: 300));

    await expectLater(target, matchesGoldenFile('goldens/app_button.png'));
  });
}
```

`app/test/design/app_fab_golden_test.dart`:
```dart
import 'package:chagocnote/design/widgets/app_fab.dart';
import 'package:flutter_test/flutter_test.dart';

import '../support/golden_frame.dart';

void _noop() {}

void main() {
  testWidgets('AppFab 골든', (tester) async {
    final target = await pumpGoldenFrame(tester, AppFab(onPressed: _noop));

    await expectLater(target, matchesGoldenFile('goldens/app_fab.png'));
  });
}
```

`app/test/design/app_glass_bar_golden_test.dart`:
```dart
import 'package:chagocnote/design/widgets/app_glass_bar.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../support/golden_frame.dart';

void _noop(int _) {}

void main() {
  testWidgets('AppGlassBar 골든 — 3슬롯, 가운데(고객) 선택', (tester) async {
    final target = await pumpGoldenFrame(
      tester,
      SizedBox(
        width: 320,
        child: AppGlassBar(
          items: const [
            AppGlassBarItem(icon: Icons.calendar_today, label: '캘린더'),
            AppGlassBarItem(icon: Icons.people_outline, label: '고객'),
            AppGlassBarItem(icon: Icons.bar_chart, label: '매출'),
          ],
          currentIndex: 1,
          onTap: _noop,
        ),
      ),
    );

    await expectLater(target, matchesGoldenFile('goldens/app_glass_bar.png'));
  });
}
```

`app/test/design/app_glass_card_golden_test.dart`:
```dart
import 'package:chagocnote/design/widgets/app_glass_card.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';

import '../support/golden_frame.dart';

void main() {
  testWidgets('AppGlassCard 골든 — 투명도 줄이기라 불투명 표면으로 그린다', (tester) async {
    final target = await pumpGoldenFrame(
      tester,
      const SizedBox(
        width: 240,
        height: 120,
        child: AppGlassCard(
          child: Text(
            '차곡노트',
            style: TextStyle(fontFamily: 'Pretendard', fontSize: 24),
          ),
        ),
      ),
    );

    await expectLater(target, matchesGoldenFile('goldens/app_glass_card.png'));
  });
}
```

`app/test/design/app_sheet_golden_test.dart`:
```dart
import 'package:chagocnote/design/app_theme.dart';
import 'package:chagocnote/design/bridge/glass_surface.dart';
import 'package:chagocnote/design/widgets/app_sheet.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('AppSheet 골든 — 연 상태의 전체 화면', (tester) async {
    tester.view.physicalSize = const Size(390, 700);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      MaterialApp(
        theme: appTheme(),
        debugShowCheckedModeBanner: false,
        home: GlassBridge(
          factory: const OpaqueSurfaceFactory(),
          child: AppBackground(
            child: Scaffold(
              backgroundColor: Colors.transparent,
              body: Builder(
                builder: (context) => Center(
                  child: ElevatedButton(
                    onPressed: () => AppSheet.show<void>(
                      context,
                      builder: (context) => const Padding(
                        padding: EdgeInsets.only(bottom: 24),
                        child: Text(
                          '시트 내용',
                          style: TextStyle(fontFamily: 'Pretendard', fontSize: 16),
                        ),
                      ),
                    ),
                    child: const Text('열기'),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );

    await tester.tap(find.text('열기'));
    await tester.pumpAndSettle();

    await expectLater(
      find.byType(MaterialApp),
      matchesGoldenFile('goldens/app_sheet.png'),
    );
  });
}
```

`app/test/design/app_segment_golden_test.dart`:
```dart
import 'package:chagocnote/design/widgets/app_segment.dart';
import 'package:flutter_test/flutter_test.dart';

import '../support/golden_frame.dart';

void _noop(int _) {}

void main() {
  testWidgets('AppSegment 골든 — "캘린더" 선택', (tester) async {
    final target = await pumpGoldenFrame(
      tester,
      AppSegment(
        labels: const ['캘린더', '기록'],
        currentIndex: 0,
        onChanged: _noop,
      ),
    );

    await expectLater(target, matchesGoldenFile('goldens/app_segment.png'));
  });
}
```

`app/test/design/app_photo_tile_golden_test.dart`:
```dart
import 'package:chagocnote/design/widgets/app_photo_tile.dart';
import 'package:flutter_test/flutter_test.dart';

import '../support/golden_frame.dart';

void main() {
  testWidgets('AppPhotoTile 골든 — 플레이스홀더 + 개수', (tester) async {
    final target = await pumpGoldenFrame(
      tester,
      const AppPhotoTile(image: null, count: 3),
    );

    await expectLater(target, matchesGoldenFile('goldens/app_photo_tile.png'));
  });
}
```

`app/test/design/app_big_date_golden_test.dart`:
```dart
import 'package:chagocnote/design/widgets/app_big_date.dart';
import 'package:flutter_test/flutter_test.dart';

import '../support/golden_frame.dart';

void main() {
  testWidgets('AppBigDate 골든 — 2026-09-22', (tester) async {
    final target = await pumpGoldenFrame(
      tester,
      AppBigDate(date: DateTime(2026, 9, 22)),
    );

    await expectLater(target, matchesGoldenFile('goldens/app_big_date.png'));
  });
}
```

`app/test/design/app_chip_golden_test.dart`:
```dart
import 'package:chagocnote/design/widgets/app_chip.dart';
import 'package:flutter_test/flutter_test.dart';

import '../support/golden_frame.dart';

void main() {
  testWidgets('AppChip 골든 — 완료', (tester) async {
    final target = await pumpGoldenFrame(tester, const AppChip(label: '완료'));

    await expectLater(target, matchesGoldenFile('goldens/app_chip.png'));
  });
}
```

Run: `flutter test test/design`
Expected: FAIL — `Not found: 'package:chagocnote/design/widgets/app_button.dart'` 등

- [ ] **Step 2: 위젯을 구현한다**

`app/lib/design/widgets/app_button.dart`:
```dart
import 'package:flutter/material.dart';

import '../tokens/app_colors.dart';
import '../tokens/app_radius.dart';
import '../tokens/app_spacing.dart';
import '../tokens/app_typography.dart';
import 'pressable.dart';

/// 알약 모양 버튼("기록 수정" 등).
///
/// `filled`이면 잉크색 채움 + 흰 글자, 아니면 아웃라인. `busy`면 작은
/// 스피너를 보여주고 탭을 막는다. `onPressed`가 null이거나 `busy`면
/// 비활성 색(보조 텍스트 색)으로 그린다.
class AppButton extends StatelessWidget {
  const AppButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.filled = false,
    this.busy = false,
    this.icon,
  });

  final String label;
  final VoidCallback? onPressed;
  final bool filled;
  final bool busy;
  final IconData? icon;

  bool get _enabled => onPressed != null && !busy;

  @override
  Widget build(BuildContext context) {
    final Color background = filled
        ? (_enabled ? AppColors.ink : AppColors.line)
        : Colors.transparent;
    final Color foreground = filled
        ? AppColors.white
        : (_enabled ? AppColors.ink : AppColors.secondary);
    final Color borderColor = _enabled ? AppColors.ink : AppColors.secondary;

    return Pressable(
      onTap: _enabled ? onPressed : null,
      semanticLabel: label,
      child: Container(
        height: 44,
        padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
        decoration: BoxDecoration(
          color: background,
          borderRadius: BorderRadius.circular(AppRadius.pill),
          border: filled ? null : Border.all(color: borderColor, width: 1),
        ),
        alignment: Alignment.center,
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (busy) ...[
              SizedBox(
                width: 14,
                height: 14,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  valueColor: AlwaysStoppedAnimation<Color>(foreground),
                ),
              ),
              const SizedBox(width: AppSpacing.sm),
            ] else if (icon != null) ...[
              Icon(icon, size: 16, color: foreground),
              const SizedBox(width: AppSpacing.sm),
            ],
            Text(label, style: AppTypography.bodyStrong.copyWith(color: foreground)),
          ],
        ),
      ),
    );
  }
}
```

`app/lib/design/widgets/app_fab.dart`:
```dart
import 'package:flutter/material.dart';

import '../tokens/app_colors.dart';
import 'pressable.dart';

/// 검정 원 + 흰 더하기 아이콘의 플로팅 액션 버튼.
class AppFab extends StatelessWidget {
  const AppFab({
    super.key,
    required this.onPressed,
    this.icon = Icons.add,
    this.semanticLabel,
  });

  final VoidCallback onPressed;
  final IconData icon;
  final String? semanticLabel;

  @override
  Widget build(BuildContext context) {
    return Pressable(
      onTap: onPressed,
      semanticLabel: semanticLabel ?? '추가',
      child: Container(
        width: 50,
        height: 50,
        decoration: const BoxDecoration(
          color: AppColors.ink,
          shape: BoxShape.circle,
        ),
        alignment: Alignment.center,
        child: Icon(icon, color: AppColors.white, size: 22),
      ),
    );
  }
}
```

`app/lib/design/widgets/app_glass_bar.dart`:
```dart
import 'package:flutter/widgets.dart';

import '../bridge/glass_surface.dart';
import '../tokens/app_colors.dart';
import '../tokens/app_radius.dart';
import '../tokens/app_spacing.dart';
import '../tokens/app_typography.dart';
import 'pressable.dart';

/// [AppGlassBar]의 슬롯 하나(아이콘 + 라벨).
class AppGlassBarItem {
  const AppGlassBarItem({required this.icon, required this.label});

  final IconData icon;
  final String label;
}

/// 하단 3슬롯 유리 탭바(캘린더 · 고객 · 매출).
///
/// 선택된 슬롯은 잉크 색, 나머지는 보조 색으로 그린다.
class AppGlassBar extends StatelessWidget {
  const AppGlassBar({
    super.key,
    required this.items,
    required this.currentIndex,
    required this.onTap,
  });

  final List<AppGlassBarItem> items;
  final int currentIndex;
  final ValueChanged<int> onTap;

  @override
  Widget build(BuildContext context) {
    return GlassSurface(
      borderRadius: const BorderRadius.all(Radius.circular(AppRadius.pill)),
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.sm),
      child: SizedBox(
        height: 56,
        child: Row(
          children: [
            for (var i = 0; i < items.length; i++)
              Expanded(
                child: _BarItem(
                  item: items[i],
                  selected: i == currentIndex,
                  onTap: () => onTap(i),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _BarItem extends StatelessWidget {
  const _BarItem({
    required this.item,
    required this.selected,
    required this.onTap,
  });

  final AppGlassBarItem item;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final color = selected ? AppColors.ink : AppColors.secondary;
    return Pressable(
      onTap: onTap,
      semanticLabel: item.label,
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(item.icon, size: 19, color: color),
          const SizedBox(height: 2),
          Text(
            item.label,
            style: AppTypography.caption.copyWith(
              color: color,
              fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }
}
```

`app/lib/design/widgets/app_glass_card.dart`:
```dart
import 'package:flutter/widgets.dart';

import '../bridge/glass_surface.dart';
import '../tokens/app_radius.dart';
import '../tokens/app_spacing.dart';

/// 앱 전역에서 쓰는 반투명 유리 카드.
///
/// 실제 렌더링은 [GlassSurface]에 위임한다 — "투명도 줄이기"가 켜져
/// 있으면 자동으로 불투명 대체 표면을 쓴다.
class AppGlassCard extends StatelessWidget {
  const AppGlassCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(AppSpacing.lg),
  });

  final Widget child;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) {
    return GlassSurface(
      borderRadius: const BorderRadius.all(Radius.circular(AppRadius.lg)),
      padding: padding,
      child: child,
    );
  }
}
```

`app/lib/design/widgets/app_sheet.dart`:
```dart
import 'package:flutter/material.dart';

import '../tokens/app_colors.dart';
import '../tokens/app_radius.dart';
import '../tokens/app_spacing.dart';
import 'app_glass_card.dart';

/// 유리 표면 위, 잡이(grabber)가 달린 드래그-해제 바텀시트.
///
/// 드래그로 닫는 동작은 `showModalBottomSheet`의 기본 `enableDrag`를
/// 그대로 쓴다 — 별도 제스처 코드를 새로 만들지 않는다.
abstract final class AppSheet {
  static Future<T?> show<T>(
    BuildContext context, {
    required WidgetBuilder builder,
  }) {
    return showModalBottomSheet<T>(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (context) => _AppSheetShell(builder: builder),
    );
  }
}

class _AppSheetShell extends StatelessWidget {
  const _AppSheetShell({required this.builder});

  final WidgetBuilder builder;

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: AppGlassCard(
          padding: const EdgeInsets.symmetric(
            vertical: AppSpacing.md,
            horizontal: AppSpacing.lg,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 36,
                height: 4,
                margin: const EdgeInsets.only(bottom: AppSpacing.md),
                decoration: BoxDecoration(
                  color: AppColors.line,
                  borderRadius: BorderRadius.circular(AppRadius.pill),
                ),
              ),
              builder(context),
            ],
          ),
        ),
      ),
    );
  }
}
```

`app/lib/design/widgets/app_segment.dart`:
```dart
import 'package:flutter/widgets.dart';

import '../tokens/app_colors.dart';
import '../tokens/app_spacing.dart';
import '../tokens/app_typography.dart';
import 'pressable.dart';

/// 밑줄로 선택 상태를 표시하는 텍스트 탭("캘린더 · 기록").
class AppSegment extends StatelessWidget {
  const AppSegment({
    super.key,
    required this.labels,
    required this.currentIndex,
    required this.onChanged,
  });

  final List<String> labels;
  final int currentIndex;
  final ValueChanged<int> onChanged;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        for (var i = 0; i < labels.length; i++) ...[
          if (i > 0) const SizedBox(width: AppSpacing.lg),
          _SegmentTab(
            label: labels[i],
            selected: i == currentIndex,
            onTap: () => onChanged(i),
          ),
        ],
      ],
    );
  }
}

class _SegmentTab extends StatelessWidget {
  const _SegmentTab({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final color = selected ? AppColors.ink : AppColors.secondary;
    return Pressable(
      onTap: onTap,
      semanticLabel: label,
      // IntrinsicWidth로 밑줄 너비를 텍스트 너비에 맞춘다. Row 안에서
      // flex가 아닌 자식은 주축 폭이 무한대로 느슨하게 주어지는데,
      // IntrinsicWidth가 그 안에서 실제 필요한 유한 폭을 계산해준다.
      child: IntrinsicWidth(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              label,
              textAlign: TextAlign.center,
              style: AppTypography.body.copyWith(
                color: color,
                fontWeight: selected ? FontWeight.w700 : FontWeight.w400,
              ),
            ),
            const SizedBox(height: AppSpacing.xs),
            Container(
              height: 2,
              color: selected ? AppColors.ink : const Color(0x00000000),
            ),
          ],
        ),
      ),
    );
  }
}
```

`app/lib/design/widgets/app_photo_tile.dart`:
```dart
import 'package:flutter/widgets.dart';

import '../tokens/app_colors.dart';
import '../tokens/app_radius.dart';
import '../tokens/app_shadows.dart';
import '../tokens/app_typography.dart';

/// 흰 테두리의 둥근 사각형 사진 타일.
///
/// `count`를 주면 안쪽 우측 하단에 흰 동그라미 숫자를 얹는다. `image`가
/// null이면 선(line) 색 플레이스홀더를 보여준다.
class AppPhotoTile extends StatelessWidget {
  const AppPhotoTile({
    super.key,
    required this.image,
    this.count,
    this.size = 72,
  });

  final ImageProvider? image;
  final int? count;
  final double size;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: size,
      height: size,
      child: Stack(
        children: [
          Positioned.fill(
            child: Container(
              decoration: BoxDecoration(
                color: image == null ? AppColors.line : null,
                image: image != null
                    ? DecorationImage(image: image!, fit: BoxFit.cover)
                    : null,
                borderRadius: BorderRadius.circular(AppRadius.md),
                border: Border.all(color: AppColors.white, width: 1.5),
                boxShadow: AppShadows.soft,
              ),
            ),
          ),
          if (count != null)
            Positioned(
              right: 4,
              bottom: 4,
              child: Container(
                width: 16,
                height: 16,
                decoration: const BoxDecoration(
                  color: AppColors.white,
                  shape: BoxShape.circle,
                  boxShadow: [
                    BoxShadow(
                      color: Color(0x33000000),
                      blurRadius: 3,
                      offset: Offset(0, 1),
                    ),
                  ],
                ),
                alignment: Alignment.center,
                child: Text(
                  '$count',
                  style: AppTypography.caption.copyWith(
                    fontSize: 9,
                    height: 1,
                    fontWeight: FontWeight.w700,
                    color: AppColors.ink,
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
```

`app/lib/design/widgets/app_big_date.dart`:
```dart
import 'package:flutter/widgets.dart';

import '../tokens/app_colors.dart';
import '../tokens/app_spacing.dart';
import '../tokens/app_typography.dart';

/// 큰 세리프 날짜 숫자 + 기울인 영문 월·요일.
///
/// `intl` 없이 영문 월/요일 이름 표를 직접 들고 있는다(요구사항 — 이 두
/// 표 말고는 지역화하지 않는다).
class AppBigDate extends StatelessWidget {
  const AppBigDate({super.key, required this.date});

  final DateTime date;

  static const _months = [
    'January',
    'February',
    'March',
    'April',
    'May',
    'June',
    'July',
    'August',
    'September',
    'October',
    'November',
    'December',
  ];

  static const _weekdays = [
    'Monday',
    'Tuesday',
    'Wednesday',
    'Thursday',
    'Friday',
    'Saturday',
    'Sunday',
  ];

  /// 일(day) 숫자만 뽑아낸 문자열("22").
  String get dayText => date.day.toString();

  /// 영문 월 이름("September").
  String get monthText => _months[date.month - 1];

  /// 영문 요일 이름("Tuesday").
  String get weekdayText => _weekdays[date.weekday - 1];

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.end,
      children: [
        Text(dayText, style: AppTypography.bigNumeral),
        const SizedBox(width: AppSpacing.sm),
        Padding(
          padding: const EdgeInsets.only(bottom: AppSpacing.xs),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(monthText, style: AppTypography.italicLabel),
              Text(
                weekdayText,
                style: AppTypography.italicLabel.copyWith(
                  fontSize: 14,
                  height: 1.2,
                  color: AppColors.secondary,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
```

`app/lib/design/widgets/app_chip.dart`:
```dart
import 'package:flutter/widgets.dart';

import '../tokens/app_colors.dart';
import '../tokens/app_radius.dart';
import '../tokens/app_spacing.dart';
import '../tokens/app_typography.dart';

/// 상태 칩("완료" 등). 탭할 수 없는 표시 전용 요소라 [Pressable]을 쓰지
/// 않는다.
class AppChip extends StatelessWidget {
  const AppChip({super.key, required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: label,
      child: Container(
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.md,
          vertical: AppSpacing.xs,
        ),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(AppRadius.pill),
          border: Border.all(color: AppColors.secondary, width: 1),
        ),
        child: Text(
          label,
          style: AppTypography.caption.copyWith(color: AppColors.ink),
        ),
      ),
    );
  }
}
```

- [ ] **Step 3: 골든을 만들고 눈으로 확인한다**

Run:
```bash
flutter test --update-goldens test/design
flutter test test/design
flutter test test/design
```
Expected: 첫 줄이 `test/design/goldens/*.png` 9개를 만든다. 뒤의 두 번은 `All tests passed!` (25개) — 두 번 돌리는 것은 골든이 결정적인지 보려는 것이다.

**만들어진 PNG 9개를 하나씩 열어 본다**(Read 도구로 이미지를 볼 수 있다). 확인할 것: 글자가 네모(Ahem)가 아니라 진짜 글리프다 / 아이콘이 빈 네모가 아니다 / 노랑·검정 줄무늬(overflow)가 없다 / 색이 여섯 값 안에 있다 / `app_big_date.png` 에 큰 세리프 "22" 와 기울인 "September", "Tuesday" 가 보인다. 하나라도 아니면 위젯이나 글꼴 로더를 고치고 다시 만든다. 보고서에 위젯마다 한 줄씩 본 것을 적는다.

- [ ] **Step 4: 전체 확인과 커밋**

Run: `flutter test && flutter analyze`
Expected: `All tests passed!`, `No issues found!`

```bash
git add app/lib/design/widgets app/test/design
git commit -m "feat(app): 기본 위젯 9개와 골든 테스트 (글래스는 불투명 대체 면으로 찍는다)"
```

### Task 4: 오류 모델·오류 문구·기기 저장소

**Files:**
- Create: `app/lib/core/error/api_exception.dart`, `app/lib/core/error/error_messages.dart`
- Create: `app/lib/core/storage/token_store.dart`, `app/lib/core/storage/prefs_store.dart`
- Test: `app/test/core/error/error_messages_test.dart`, `app/test/core/storage/stores_test.dart`

**Interfaces:**
- Consumes: Task 1 의 패키지 이름 `chagocnote`, 의존성 `dio`·`flutter_secure_storage`
- Produces:
  - `class ApiException implements Exception { int? statusCode; String code; String message; bool get isNetwork; ApiException.network(String); ApiException.fromDioException(DioException); ApiException.fromResponseData({statusCode, data}); }` — 코드 `NETWORK`(연결·타임아웃), `HTTP_ERROR`(`{code,message}` 가 아닌 응답)
  - `String messageFor(Object error)` — 화면에 보여 줄 한 줄
  - `abstract class TokenStore { Future<String?> readAccess(); Future<String?> readRefresh(); Future<void> save({required String access, required String refresh}); Future<void> clear(); }` + `SecureTokenStore`, `MemoryTokenStore`
  - `abstract class PrefsStore { Future<int?> readLastShopId(); Future<void> writeLastShopId(int shopId); Future<void> clear(); }` + `SecurePrefsStore`, `MemoryPrefsStore`

이 작업의 코드는 계획을 쓰기 전에 실험 프로젝트에서 `flutter test`·`flutter analyze` 를 통과시킨 것이다. 그래도 **검토자는 검토되지 않은 코드로 본다.**

규칙
- `ApiException.toString()` 과 모든 저장소 클래스는 토큰 값을 문자열로 내놓지 않는다(점검표 S4). `TokenStore` 에 `toString` 을 만들지 않는다.
- 화면 문구는 서버의 `message` 가 아니라 `code` 로 고른다. 설계 문서 7절의 코드는 하나도 빠지지 않는다 — 테스트가 목록으로 확인한다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`app/test/core/error/error_messages_test.dart`:
```dart
import 'package:chagocnote/core/error/api_exception.dart';
import 'package:chagocnote/core/error/error_messages.dart';
import 'package:flutter_test/flutter_test.dart';

ApiException _error(String code, {String message = '서버 문구', int? status = 400}) =>
    ApiException(statusCode: status, code: code, message: message);

void main() {
  test('아는 코드는 서버 문구가 아니라 앱의 문구를 쓴다', () {
    expect(messageFor(_error('INVITE_EXPIRED')), '만료된 초대 코드입니다. 새 코드를 받아 주세요.');
    expect(messageFor(_error('REAUTH_REQUIRED', status: 403)), '보안을 위해 다시 로그인해 주세요.');
  });

  test('모르는 코드는 서버 문구를 쓴다', () {
    expect(messageFor(_error('SOMETHING_NEW', message: '새로 생긴 안내')), '새로 생긴 안내');
  });

  test('형식을 모르는 응답과 예외가 아닌 오류는 일반 문구다', () {
    const fallback = '문제가 생겼습니다. 잠시 뒤에 다시 시도해 주세요.';
    expect(messageFor(_error('HTTP_ERROR', message: '상태 코드 500 응답을 처리할 수 없습니다.')), fallback);
    expect(messageFor(StateError('x')), fallback);
  });

  test('네트워크 오류는 다시 시도를 안내한다', () {
    expect(messageFor(ApiException.network('timeout')), contains('다시 시도'));
  });

  test('설계 문서 7절의 코드는 모두 앱의 문구가 있다', () {
    const codes = [
      'UNAUTHENTICATED', 'LAST_OWNER', 'ALREADY_A_MEMBER', 'NOT_A_MEMBER', 'PERMISSION_DENIED',
      'ACCOUNT_SUSPENDED', 'SHOP_CLOSED', 'SHOP_SUSPENDED', 'MEMBER_NOT_FOUND', 'IDENTITY_NOT_FOUND',
      'INVITE_INVALID', 'INVITE_EXPIRED', 'INVITE_EXHAUSTED', 'IDENTITY_ALREADY_LINKED',
      'PROVIDER_ALREADY_LINKED', 'LAST_IDENTITY', 'OWNERSHIP_TRANSFER_REQUIRED',
      'SHOP_CLOSE_CONFIRM_REQUIRED', 'TOO_MANY_ATTEMPTS', 'PROVIDER_VERIFICATION_FAILED',
      'REAUTH_REQUIRED', 'VALIDATION_ERROR', 'PROVIDER_NOT_SUPPORTED',
    ];
    for (final code in codes) {
      expect(messageFor(_error(code, message: '서버 문구')), isNot('서버 문구'), reason: code);
    }
  });
}
```

`app/test/core/storage/stores_test.dart`:
```dart
import 'package:chagocnote/core/storage/prefs_store.dart';
import 'package:chagocnote/core/storage/token_store.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('토큰을 저장하고 읽고 지운다', () async {
    final store = MemoryTokenStore();
    expect(await store.readAccess(), isNull);
    await store.save(access: 'a', refresh: 'r');
    expect([await store.readAccess(), await store.readRefresh()], ['a', 'r']);
    await store.clear();
    expect([await store.readAccess(), await store.readRefresh()], [null, null]);
  });

  test('마지막으로 고른 매장을 기억하고 지운다', () async {
    final prefs = MemoryPrefsStore();
    expect(await prefs.readLastShopId(), isNull);
    await prefs.writeLastShopId(3);
    expect(await prefs.readLastShopId(), 3);
    await prefs.clear();
    expect(await prefs.readLastShopId(), isNull);
  });
}
```

- [ ] **Step 2: 실패를 확인한다**

Run (`app/` 에서): `flutter test test/core`
Expected: FAIL — `Error: Not found: 'package:chagocnote/core/error/api_exception.dart'`

- [ ] **Step 3: 구현한다**

`app/lib/core/error/api_exception.dart`:
```dart
import 'package:dio/dio.dart';

/// 서버·네트워크에서 발생한 오류를 통일된 형태로 감싼다.
///
/// 서버 오류 바디는 `{"code": "...", "message": "..."}` 형태를 따른다.
/// 이 형태로 파싱되지 않으면 `HTTP_ERROR`로, 연결/타임아웃류 오류는
/// `NETWORK`로 코드를 매긴다.
class ApiException implements Exception {
  ApiException({
    required this.statusCode,
    required this.code,
    required this.message,
  });

  /// 네트워크 오류(연결 실패, 타임아웃)를 나타내는 [ApiException]을 만든다.
  factory ApiException.network(String message) => ApiException(
        statusCode: null,
        code: 'NETWORK',
        message: message,
      );

  /// [DioException]으로부터 [ApiException]을 만든다.
  factory ApiException.fromDioException(DioException error) {
    if (_isNetworkType(error.type)) {
      return ApiException.network(error.message ?? '네트워크 오류가 발생했습니다.');
    }

    final response = error.response;
    if (response == null) {
      return ApiException.network(error.message ?? '네트워크 오류가 발생했습니다.');
    }

    return ApiException.fromResponseData(
      statusCode: response.statusCode,
      data: response.data,
    );
  }

  /// 응답 바디에서 `{code, message}`를 파싱한다. 실패하면 `HTTP_ERROR`로 대체한다.
  factory ApiException.fromResponseData({
    required int? statusCode,
    required Object? data,
  }) {
    if (data is Map) {
      final code = data['code'];
      final message = data['message'];
      if (code is String && message is String) {
        return ApiException(
          statusCode: statusCode,
          code: code,
          message: message,
        );
      }
    }
    return ApiException(
      statusCode: statusCode,
      code: 'HTTP_ERROR',
      message: '상태 코드 $statusCode 응답을 처리할 수 없습니다.',
    );
  }

  static bool _isNetworkType(DioExceptionType type) {
    switch (type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.receiveTimeout:
      case DioExceptionType.connectionError:
        return true;
      case DioExceptionType.badCertificate:
      case DioExceptionType.badResponse:
      case DioExceptionType.cancel:
      case DioExceptionType.unknown:
      case DioExceptionType.transformTimeout:
        return false;
    }
  }

  final int? statusCode;
  final String code;
  final String message;

  bool get isNetwork => code == 'NETWORK';

  @override
  String toString() => 'ApiException(statusCode: $statusCode, code: $code, message: $message)';
}
```

`app/lib/core/error/error_messages.dart`:
```dart
import 'api_exception.dart';

/// 서버 오류 코드를 사용자에게 보여 줄 한국어 문구로 바꾼다.
///
/// 문구는 서버의 `message` 가 아니라 `code` 로 고른다. 모르는 코드일 때만 서버 문구를 쓴다.
const Map<String, String> _messages = {
  'NETWORK': '네트워크 연결을 확인하고 다시 시도해 주세요.',
  'UNAUTHENTICATED': '보안을 위해 다시 로그인해 주세요.',
  'REAUTH_REQUIRED': '보안을 위해 다시 로그인해 주세요.',
  'PROVIDER_VERIFICATION_FAILED': '로그인 정보를 확인하지 못했습니다. 다시 시도해 주세요.',
  'PROVIDER_NOT_SUPPORTED': '지원하지 않는 로그인 방식입니다.',
  'ACCOUNT_SUSPENDED': '이용이 정지된 계정입니다. 고객센터에 문의해 주세요.',
  'NOT_A_MEMBER': '이 매장의 멤버가 아니거나 역할이 바뀌었습니다.',
  'PERMISSION_DENIED': '이 작업을 할 권한이 없습니다.',
  'SHOP_CLOSED': '닫힌 매장입니다.',
  'SHOP_SUSPENDED': '이용이 정지된 매장입니다.',
  'MEMBER_NOT_FOUND': '멤버를 찾을 수 없습니다.',
  'IDENTITY_NOT_FOUND': '연결되어 있지 않은 로그인 수단입니다.',
  'INVITE_INVALID': '초대 코드를 확인해 주세요.',
  'INVITE_EXPIRED': '만료된 초대 코드입니다. 새 코드를 받아 주세요.',
  'INVITE_EXHAUSTED': '이미 사용된 초대 코드입니다. 새 코드를 받아 주세요.',
  'LAST_OWNER': '매장에는 사장이 한 명 이상 있어야 합니다.',
  'ALREADY_A_MEMBER': '이미 이 매장의 멤버입니다.',
  'IDENTITY_ALREADY_LINKED': '다른 계정에 연결된 로그인 수단입니다.',
  'PROVIDER_ALREADY_LINKED': '같은 종류의 로그인 수단이 이미 연결되어 있습니다.',
  'LAST_IDENTITY': '마지막 로그인 수단은 해제할 수 없습니다.',
  'OWNERSHIP_TRANSFER_REQUIRED': '혼자 사장인 매장에 다른 멤버가 있습니다. 먼저 다른 사장을 지정해 주세요.',
  'SHOP_CLOSE_CONFIRM_REQUIRED': '탈퇴하면 혼자 운영하는 매장도 함께 닫힙니다.',
  'VALIDATION_ERROR': '입력한 내용을 확인해 주세요.',
  'TOO_MANY_ATTEMPTS': '시도가 너무 잦습니다. 잠시 뒤에 다시 해 주세요.',
};

const String _fallback = '문제가 생겼습니다. 잠시 뒤에 다시 시도해 주세요.';

/// 어떤 오류든 화면에 보여 줄 문구 한 줄로 바꾼다.
String messageFor(Object error) {
  if (error is! ApiException) return _fallback;
  final known = _messages[error.code];
  if (known != null) return known;
  // HTTP_ERROR 는 서버가 {code, message} 를 주지 못한 경우라 기술적인 문구다. 보여 주지 않는다.
  if (error.code == 'HTTP_ERROR' || error.message.isEmpty) return _fallback;
  return error.message;
}
```

`app/lib/core/storage/token_store.dart`:
```dart
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// 액세스·리프레시 토큰을 저장·조회·삭제하는 저장소 인터페이스.
abstract class TokenStore {
  Future<String?> readAccess();
  Future<String?> readRefresh();
  Future<void> save({required String access, required String refresh});
  Future<void> clear();
}

/// flutter_secure_storage 로 토큰을 보관하는 구현체.
class SecureTokenStore implements TokenStore {
  SecureTokenStore({FlutterSecureStorage? storage})
      : _storage = storage ?? const FlutterSecureStorage();

  static const _accessKey = 'access_token';
  static const _refreshKey = 'refresh_token';

  final FlutterSecureStorage _storage;

  @override
  Future<String?> readAccess() => _storage.read(key: _accessKey);

  @override
  Future<String?> readRefresh() => _storage.read(key: _refreshKey);

  @override
  Future<void> save({required String access, required String refresh}) async {
    await _storage.write(key: _accessKey, value: access);
    await _storage.write(key: _refreshKey, value: refresh);
  }

  @override
  Future<void> clear() async {
    await _storage.delete(key: _accessKey);
    await _storage.delete(key: _refreshKey);
  }
}

/// 테스트용 인메모리 저장소.
class MemoryTokenStore implements TokenStore {
  String? _access;
  String? _refresh;

  @override
  Future<String?> readAccess() async => _access;

  @override
  Future<String?> readRefresh() async => _refresh;

  @override
  Future<void> save({required String access, required String refresh}) async {
    _access = access;
    _refresh = refresh;
  }

  @override
  Future<void> clear() async {
    _access = null;
    _refresh = null;
  }
}
```

`app/lib/core/storage/prefs_store.dart`:
```dart
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// 기기에 남기는 작은 설정. 지금은 "마지막으로 고른 매장" 하나다.
///
/// 저장소 패키지를 늘리지 않으려고 보안 저장소를 같이 쓴다.
abstract class PrefsStore {
  Future<int?> readLastShopId();
  Future<void> writeLastShopId(int shopId);
  Future<void> clear();
}

class SecurePrefsStore implements PrefsStore {
  SecurePrefsStore([FlutterSecureStorage? storage])
      : _storage = storage ?? const FlutterSecureStorage();

  static const _lastShopKey = 'last_shop_id';
  final FlutterSecureStorage _storage;

  @override
  Future<int?> readLastShopId() async => int.tryParse(await _storage.read(key: _lastShopKey) ?? '');

  @override
  Future<void> writeLastShopId(int shopId) => _storage.write(key: _lastShopKey, value: '$shopId');

  @override
  Future<void> clear() => _storage.delete(key: _lastShopKey);
}

class MemoryPrefsStore implements PrefsStore {
  int? _lastShopId;

  @override
  Future<int?> readLastShopId() async => _lastShopId;

  @override
  Future<void> writeLastShopId(int shopId) async => _lastShopId = shopId;

  @override
  Future<void> clear() async => _lastShopId = null;
}
```

- [ ] **Step 4: 통과를 확인한다**

Run: `flutter test test/core && flutter analyze`
Expected: `All tests passed!` (7개), `No issues found!`

- [ ] **Step 5: 커밋**

```bash
git add app/lib/core/error app/lib/core/storage app/test/core
git commit -m "feat(app): 서버 오류 모델과 한국어 문구, 토큰·설정 저장소를 둔다"
```

### Task 5: ApiClient — 토큰 첨부, 단일 갱신, 한 번 재시도

이 계획에서 가장 조심할 작업이다. 백엔드는 **이미 쓴 리프레시 토큰이 다시 오면 그 유저의 모든 기기를 로그아웃시키고, 유예가 없다**(사용자 결정). 앱이 갱신을 두 번 보내거나 실패한 갱신을 다시 보내면 정상 사용자가 전부 로그아웃된다.

**Files:**
- Create: `app/lib/core/proxy/api_client.dart`
- Create: `app/test/support/fake_http_client_adapter.dart`
- Test: `app/test/core/proxy/api_client_test.dart`

**Interfaces:**
- Consumes: Task 4 의 `ApiException`, `TokenStore`, `MemoryTokenStore`
- Produces:
  - `class ApiClient { ApiClient({required TokenStore tokenStore, String baseUrl = '', void Function()? onSessionEnded, Dio? dio, Dio? refreshDio}); Future<dynamic> get(String path, {Map<String, dynamic>? queryParameters, bool public = false}); Future<dynamic> post(String path, {Object? data, bool public = false}); put(...); patch(...); delete(String path, {Object? data, bool public = false}); }` — 디코드된 JSON(`Map`/`List`/`null`)을 돌려주고 실패하면 `ApiException` 을 던진다.
  - `public: true` 인 요청은 `Authorization` 헤더를 붙이지 않고 갱신 로직도 타지 않는다. `/v1/auth/social`·`/v1/auth/refresh`·`/v1/auth/logout` 을 부르는 쪽(Task 6)이 반드시 켠다.
  - 테스트 지원: `FakeHttpClientAdapter(FakeHandler handler)`, `FakeResponse({required int statusCode, Object? data, Map<String, List<String>>? headers})`, `adapter.requests`, `adapter.lastBodyByPath`.

동작 (점검표 S1~S4)
1. 공개가 아닌 요청이 `401 UNAUTHENTICATED` 를 받으면 갱신한다. **동시에 여러 요청이 401 을 받아도 갱신은 하나만 나간다** — 진행 중인 `Future` 하나를 나눠 기다린다. (`QueuedInterceptorsWrapper` 는 갱신과 무관한 정상 요청까지 줄 세우므로 쓰지 않는다. Dart 는 단일 스레드라 첫 `await` 앞에서 필드를 확인·대입하면 경합이 없다.)
2. 갱신에 성공하면 새 토큰을 저장하고 원 요청을 **정확히 한 번** 다시 보낸다(`dio.fetch(같은 RequestOptions)` — `onRequest` 가 다시 돌면서 저장소의 새 토큰을 붙인다). 다시 보낸 요청이 또 401 이면 오류로 끝낸다. 두 번째 갱신은 없다.
3. 갱신 요청은 인터셉터가 없는 **별도의 `Dio`** 로 보낸다(갱신의 401 이 다시 갱신을 부르는 재귀를 막는다).
4. 갱신이 실패했을 때:
   - 연결 실패·타임아웃, 게이트웨이의 502·503·504 → 요청이 백엔드에 닿지 못했다. **토큰을 지우지 않고, 세션을 끝내지 않고, 갱신을 다시 보내지도 않는다.** 원 요청은 그 오류로 실패한다. 사용자가 다음에 직접 일으킨 요청에서 한 번 더 시도된다.
   - 그 밖(401·403·500 …) → 서버가 거절했거나, 처리 도중 실패해 토큰이 이미 소모됐을 수 있다(백엔드는 토큰을 먼저 꺼낸 뒤에 유저를 조회한다). 같은 토큰을 다시 보내면 재사용 감지로 **모든 기기**가 로그아웃되므로, **이 기기의 토큰만 지우고** `onSessionEnded` 를 한 번 부른다.
5. `whenComplete` 가 만드는 파생 `Future` 는 아무도 기다리지 않는다. `.ignore()` 를 빼면 갱신 실패가 "처리되지 않은 예외"로 한 번 더 보고된다.
6. 요청·응답의 본문과 헤더를 로그로 남기지 않는다. `LogInterceptor` 를 달지 않는다.

- [ ] **Step 1: 가짜 어댑터와 실패하는 테스트를 쓴다**

`app/test/support/fake_http_client_adapter.dart`:
```dart
import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';

/// 하나의 가짜 응답 정의. [FakeHttpClientAdapter]의 핸들러가 이 값을 돌려주면
/// 그대로 [ResponseBody]로 바뀐다.
///
/// - `data`가 `Map`/`List`면 JSON으로 인코딩하고 `content-type: application/json`을 단다.
/// - `data`가 `String`이면 그대로 보내고, 기본 content-type은 `text/plain`이다
///   (JSON이 아닌 에러 바디를 흉내내려면 이 경로를 쓴다).
class FakeResponse {
  const FakeResponse({
    required this.statusCode,
    this.data,
    this.headers,
  });

  final int statusCode;
  final Object? data;
  final Map<String, List<String>>? headers;
}

typedef FakeHandler = FutureOr<FakeResponse> Function(
  RequestOptions options,
  Uint8List? body,
);

/// 네트워크 없이 dio를 구동하는 가짜 [HttpClientAdapter].
///
/// [handler]가 예외(특히 [DioException])를 던지면 그대로 위로 전파되어
/// dio가 실제 어댑터 오류처럼 처리한다 — 타임아웃/연결 오류를 흉내낼 때 쓴다.
class FakeHttpClientAdapter implements HttpClientAdapter {
  FakeHttpClientAdapter(this.handler);

  final FakeHandler handler;

  /// 어댑터를 거쳐간 모든 요청(원 요청 + 재시도 + 리프레시 포함), 도착 순서대로.
  final List<RequestOptions> requests = [];

  /// 경로별 마지막 요청 바디(원문 바이트). DELETE 바디 전송 검증 등에 쓴다.
  final Map<String, Uint8List> lastBodyByPath = {};

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    requests.add(options);

    Uint8List? bytes;
    if (requestStream != null) {
      final chunks = <int>[];
      await for (final chunk in requestStream) {
        chunks.addAll(chunk);
      }
      bytes = Uint8List.fromList(chunks);
      lastBodyByPath[options.path] = bytes;
    }

    final result = await handler(options, bytes);

    final headers = <String, List<String>>{...?result.headers};
    final data = result.data;
    if (data == null) {
      return ResponseBody.fromBytes(
        const <int>[],
        result.statusCode,
        headers: headers,
      );
    }
    if (data is String) {
      headers.putIfAbsent(
        'content-type',
        () => const ['text/plain; charset=utf-8'],
      );
      return ResponseBody.fromString(
        data,
        result.statusCode,
        headers: headers,
      );
    }
    headers['content-type'] = const ['application/json; charset=utf-8'];
    return ResponseBody.fromString(
      jsonEncode(data),
      result.statusCode,
      headers: headers,
    );
  }

  @override
  void close({bool force = false}) {}
}
```

`app/test/core/proxy/api_client_test.dart`:
```dart
import 'dart:convert';
import 'dart:typed_data';

import 'package:chagocnote/core/error/api_exception.dart';
import 'package:chagocnote/core/proxy/api_client.dart';
import 'package:chagocnote/core/storage/token_store.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../support/fake_http_client_adapter.dart';

void main() {
  group('happy path', () {
    test('보호된 요청에는 저장된 액세스 토큰이 Authorization 헤더로 붙는다', () async {
      final tokenStore = MemoryTokenStore()
        ..save(access: 'old-access', refresh: 'old-refresh');
      final adapter = FakeHttpClientAdapter((options, body) {
        expect(options.headers['Authorization'], 'Bearer old-access');
        return const FakeResponse(statusCode: 200, data: {'ok': true});
      });
      final client = _buildClient(tokenStore: tokenStore, adapter: adapter);

      final result = await client.get('/protected');

      expect(result, {'ok': true});
      expect(adapter.requests, hasLength(1));
    });

    test('public 요청에는 Authorization 헤더가 붙지 않는다', () async {
      final tokenStore = MemoryTokenStore()
        ..save(access: 'old-access', refresh: 'old-refresh');
      final adapter = FakeHttpClientAdapter((options, body) {
        expect(options.headers.containsKey('Authorization'), isFalse);
        return const FakeResponse(statusCode: 200, data: {'ok': true});
      });
      final client = _buildClient(tokenStore: tokenStore, adapter: adapter);

      final result = await client.post(
        '/v1/auth/social',
        data: {'idToken': 'x'},
        public: true,
      );

      expect(result, {'ok': true});
    });
  });

  group('리프레시', () {
    test('401 UNAUTHENTICATED → 리프레시 → 원 요청 재시도 성공', () async {
      final tokenStore = MemoryTokenStore()
        ..save(access: 'expired', refresh: 'refresh-1');
      var refreshCalls = 0;
      final adapter = FakeHttpClientAdapter((options, body) {
        if (options.path == '/v1/auth/refresh') {
          refreshCalls++;
          final payload = jsonDecode(utf8.decode(body!)) as Map;
          expect(payload['refresh_token'], 'refresh-1');
          return const FakeResponse(
            statusCode: 200,
            data: {
              'access_token': 'new-access',
              'refresh_token': 'new-refresh',
              'token_type': 'bearer',
              'expires_in': 3600,
            },
          );
        }
        final auth = options.headers['Authorization'];
        if (auth == 'Bearer expired') {
          return const FakeResponse(
            statusCode: 401,
            data: {'code': 'UNAUTHENTICATED', 'message': '토큰이 만료되었습니다.'},
          );
        }
        expect(auth, 'Bearer new-access');
        return const FakeResponse(statusCode: 200, data: {'ok': true});
      });
      final client = _buildClient(tokenStore: tokenStore, adapter: adapter);

      final result = await client.get('/protected');

      expect(result, {'ok': true});
      expect(refreshCalls, 1);
      expect(await tokenStore.readAccess(), 'new-access');
      expect(await tokenStore.readRefresh(), 'new-refresh');
    });

    test('동시에 3개 요청이 401을 받아도 리프레시는 한 번만 나간다', () async {
      final tokenStore = MemoryTokenStore()
        ..save(access: 'expired', refresh: 'refresh-1');
      var refreshCalls = 0;
      final adapter = FakeHttpClientAdapter((options, body) {
        if (options.path == '/v1/auth/refresh') {
          refreshCalls++;
          return const FakeResponse(
            statusCode: 200,
            data: {
              'access_token': 'new-access',
              'refresh_token': 'new-refresh',
              'token_type': 'bearer',
              'expires_in': 3600,
            },
          );
        }
        final auth = options.headers['Authorization'];
        if (auth == 'Bearer expired') {
          return const FakeResponse(
            statusCode: 401,
            data: {'code': 'UNAUTHENTICATED', 'message': '토큰이 만료되었습니다.'},
          );
        }
        return const FakeResponse(statusCode: 200, data: {'ok': true});
      });
      final client = _buildClient(tokenStore: tokenStore, adapter: adapter);

      final results = await Future.wait([
        client.get('/protected'),
        client.get('/protected'),
        client.get('/protected'),
      ]);

      expect(results, everyElement({'ok': true}));
      expect(refreshCalls, 1);
    });

    test('재시도 요청이 다시 401을 받으면 에러로 끝나고 두 번째 리프레시는 없다', () async {
      final tokenStore = MemoryTokenStore()
        ..save(access: 'expired', refresh: 'refresh-1');
      var refreshCalls = 0;
      final adapter = FakeHttpClientAdapter((options, body) {
        if (options.path == '/v1/auth/refresh') {
          refreshCalls++;
          return const FakeResponse(
            statusCode: 200,
            data: {
              'access_token': 'new-access',
              'refresh_token': 'new-refresh',
              'token_type': 'bearer',
              'expires_in': 3600,
            },
          );
        }
        // 재시도해도 계속 401 (예: 다른 이유로 여전히 거부됨).
        return const FakeResponse(
          statusCode: 401,
          data: {'code': 'UNAUTHENTICATED', 'message': '여전히 거부됨'},
        );
      });
      final client = _buildClient(tokenStore: tokenStore, adapter: adapter);

      await expectLater(
        client.get('/protected'),
        throwsA(
          isA<ApiException>()
              .having((e) => e.code, 'code', 'UNAUTHENTICATED')
              .having((e) => e.statusCode, 'statusCode', 401),
        ),
      );
      expect(refreshCalls, 1);
    });

    test('리프레시가 401을 받으면 토큰을 지우고 onSessionEnded를 한 번만 부르며 원 요청들은 실패한다',
        () async {
      final tokenStore = MemoryTokenStore()
        ..save(access: 'expired', refresh: 'stolen-refresh');
      var sessionEndedCalls = 0;
      final adapter = FakeHttpClientAdapter((options, body) {
        if (options.path == '/v1/auth/refresh') {
          return const FakeResponse(
            statusCode: 401,
            data: {'code': 'UNAUTHENTICATED', 'message': '리프레시 토큰 재사용 탐지'},
          );
        }
        return const FakeResponse(
          statusCode: 401,
          data: {'code': 'UNAUTHENTICATED', 'message': '토큰이 만료되었습니다.'},
        );
      });
      final client = _buildClient(
        tokenStore: tokenStore,
        adapter: adapter,
        onSessionEnded: () => sessionEndedCalls++,
      );

      final expectations = [
        expectLater(
          client.get('/a'),
          throwsA(
            isA<ApiException>().having((e) => e.code, 'code', 'UNAUTHENTICATED'),
          ),
        ),
        expectLater(
          client.get('/b'),
          throwsA(
            isA<ApiException>().having((e) => e.code, 'code', 'UNAUTHENTICATED'),
          ),
        ),
        expectLater(
          client.get('/c'),
          throwsA(
            isA<ApiException>().having((e) => e.code, 'code', 'UNAUTHENTICATED'),
          ),
        ),
      ];
      await Future.wait(expectations);

      expect(sessionEndedCalls, 1);
      expect(await tokenStore.readAccess(), isNull);
      expect(await tokenStore.readRefresh(), isNull);
    });

    test('리프레시가 게이트웨이 오류(502·503·504)면 토큰을 지우지 않고 세션도 끝내지 않는다',
        () async {
      for (final status in [502, 503, 504]) {
        final tokenStore = MemoryTokenStore()
          ..save(access: 'expired', refresh: 'refresh-1');
        var refreshCalls = 0;
        var sessionEndedCalls = 0;
        final adapter = FakeHttpClientAdapter((options, body) {
          if (options.path == '/v1/auth/refresh') {
            refreshCalls++;
            return FakeResponse(statusCode: status, data: 'Bad Gateway');
          }
          return const FakeResponse(
            statusCode: 401,
            data: {'code': 'UNAUTHENTICATED', 'message': '토큰이 만료되었습니다.'},
          );
        });
        final client = _buildClient(
          tokenStore: tokenStore,
          adapter: adapter,
          onSessionEnded: () => sessionEndedCalls++,
        );

        await expectLater(
          client.get('/protected'),
          throwsA(isA<ApiException>().having((e) => e.statusCode, 'statusCode', status)),
        );

        expect(refreshCalls, 1, reason: '\$status');
        expect(sessionEndedCalls, 0, reason: '\$status');
        expect(await tokenStore.readRefresh(), 'refresh-1', reason: '\$status');
      }
    });

    test('리프레시가 500이면 토큰이 이미 소모됐을 수 있으므로 이 기기만 로그아웃한다', () async {
      final tokenStore = MemoryTokenStore()
        ..save(access: 'expired', refresh: 'refresh-1');
      var sessionEndedCalls = 0;
      final adapter = FakeHttpClientAdapter((options, body) {
        if (options.path == '/v1/auth/refresh') {
          return const FakeResponse(
            statusCode: 500,
            data: {'code': 'INTERNAL_ERROR', 'message': '서버 오류'},
          );
        }
        return const FakeResponse(
          statusCode: 401,
          data: {'code': 'UNAUTHENTICATED', 'message': '토큰이 만료되었습니다.'},
        );
      });
      final client = _buildClient(
        tokenStore: tokenStore,
        adapter: adapter,
        onSessionEnded: () => sessionEndedCalls++,
      );

      await expectLater(client.get('/protected'), throwsA(isA<ApiException>()));

      expect(sessionEndedCalls, 1);
      expect(await tokenStore.readRefresh(), isNull);
    });

    test('리프레시가 타임아웃되면 토큰은 유지되고 원 요청은 NETWORK 에러로 끝나며 리프레시는 한 번만 나간다',
        () async {
      final tokenStore = MemoryTokenStore()
        ..save(access: 'expired', refresh: 'refresh-1');
      var refreshCalls = 0;
      final adapter = FakeHttpClientAdapter((options, body) {
        if (options.path == '/v1/auth/refresh') {
          refreshCalls++;
          throw DioException.connectionTimeout(
            timeout: const Duration(seconds: 5),
            requestOptions: options,
          );
        }
        return const FakeResponse(
          statusCode: 401,
          data: {'code': 'UNAUTHENTICATED', 'message': '토큰이 만료되었습니다.'},
        );
      });
      final client = _buildClient(tokenStore: tokenStore, adapter: adapter);

      await expectLater(
        client.get('/protected'),
        throwsA(
          isA<ApiException>()
              .having((e) => e.code, 'code', 'NETWORK')
              .having((e) => e.isNetwork, 'isNetwork', isTrue),
        ),
      );

      expect(refreshCalls, 1);
      expect(await tokenStore.readAccess(), 'expired');
      expect(await tokenStore.readRefresh(), 'refresh-1');
    });
  });

  group('에러 바디 파싱', () {
    test('{code,message} JSON 바디는 그대로 ApiException으로 파싱된다', () async {
      final adapter = FakeHttpClientAdapter((options, body) {
        return const FakeResponse(
          statusCode: 403,
          data: {'code': 'ACCOUNT_SUSPENDED', 'message': '정지된 계정입니다.'},
        );
      });
      final client = _buildClient(
        tokenStore: MemoryTokenStore(),
        adapter: adapter,
      );

      await expectLater(
        client.get('/x', public: true),
        throwsA(
          isA<ApiException>()
              .having((e) => e.statusCode, 'statusCode', 403)
              .having((e) => e.code, 'code', 'ACCOUNT_SUSPENDED')
              .having((e) => e.message, 'message', '정지된 계정입니다.'),
        ),
      );
    });

    test('JSON이 아닌 에러 바디는 HTTP_ERROR로 대체된다', () async {
      final adapter = FakeHttpClientAdapter((options, body) {
        return const FakeResponse(statusCode: 500, data: 'internal error');
      });
      final client = _buildClient(
        tokenStore: MemoryTokenStore(),
        adapter: adapter,
      );

      await expectLater(
        client.get('/x', public: true),
        throwsA(
          isA<ApiException>()
              .having((e) => e.statusCode, 'statusCode', 500)
              .having((e) => e.code, 'code', 'HTTP_ERROR'),
        ),
      );
    });
  });

  group('DELETE 바디', () {
    test('DELETE 요청이 JSON 바디를 실제로 보낸다', () async {
      Uint8List? capturedBody;
      String? capturedContentType;
      final adapter = FakeHttpClientAdapter((options, body) {
        if (options.method == 'DELETE') {
          capturedBody = body;
          capturedContentType = options.headers['content-type'] as String?;
        }
        return const FakeResponse(statusCode: 200, data: {'ok': true});
      });
      final client = _buildClient(
        tokenStore: MemoryTokenStore(),
        adapter: adapter,
      );

      final result = await client.delete(
        '/v1/auth/account',
        data: {'confirm_close_shops': true},
        public: true,
      );

      expect(result, {'ok': true});
      expect(capturedBody, isNotNull);
      expect(
        jsonDecode(utf8.decode(capturedBody!)),
        {'confirm_close_shops': true},
      );
      expect(capturedContentType, contains('application/json'));
    });
  });
}

ApiClient _buildClient({
  required TokenStore tokenStore,
  required FakeHttpClientAdapter adapter,
  void Function()? onSessionEnded,
}) {
  final dio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final refreshDio = Dio(BaseOptions())..httpClientAdapter = adapter;
  return ApiClient(
    tokenStore: tokenStore,
    onSessionEnded: onSessionEnded,
    dio: dio,
    refreshDio: refreshDio,
  );
}
```

- [ ] **Step 2: 실패를 확인한다**

Run: `flutter test test/core/proxy`
Expected: FAIL — `Error: Not found: 'package:chagocnote/core/proxy/api_client.dart'`

- [ ] **Step 3: 구현한다**

`app/lib/core/proxy/api_client.dart`:
```dart
import 'package:dio/dio.dart';

import '../error/api_exception.dart';
import '../storage/token_store.dart';

/// 액세스 토큰 부착, 401 발생 시 단일 비행(single-flight) 리프레시,
/// 원 요청 1회 재시도를 담당하는 HTTP 클라이언트.
///
/// 리프레시 요청은 별도의 "민짜" [Dio] 인스턴스로 보낸다. 같은 인터셉터를
/// 태우면 리프레시 요청 자체가 401을 받았을 때 다시 리프레시를 시도하는
/// 재귀에 빠질 수 있기 때문이다.
class ApiClient {
  ApiClient({
    required this._tokenStore,
    String baseUrl = '',
    this._onSessionEnded,
    Dio? dio,
    Dio? refreshDio,
  })  : _dio = dio ?? Dio(BaseOptions(baseUrl: baseUrl)),
        _refreshDio = refreshDio ?? Dio(BaseOptions(baseUrl: baseUrl)) {
    _dio.interceptors.add(
      InterceptorsWrapper(onRequest: _onRequest, onError: _onError),
    );
  }

  final TokenStore _tokenStore;
  final void Function()? _onSessionEnded;
  final Dio _dio;
  final Dio _refreshDio;

  /// 진행 중인 리프레시. 동시에 여러 요청이 401을 받아도 리프레시는
  /// 하나만 나가도록(single-flight) 이 필드를 공유한다.
  Future<void>? _refreshFuture;

  static const _gatewayFailures = {502, 503, 504};

  Future<dynamic> get(
    String path, {
    Map<String, dynamic>? queryParameters,
    bool public = false,
  }) =>
      _send('GET', path, queryParameters: queryParameters, public: public);

  Future<dynamic> post(String path, {Object? data, bool public = false}) =>
      _send('POST', path, data: data, public: public);

  Future<dynamic> put(String path, {Object? data, bool public = false}) =>
      _send('PUT', path, data: data, public: public);

  Future<dynamic> patch(String path, {Object? data, bool public = false}) =>
      _send('PATCH', path, data: data, public: public);

  Future<dynamic> delete(String path, {Object? data, bool public = false}) =>
      _send('DELETE', path, data: data, public: public);

  Future<dynamic> _send(
    String method,
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
    bool public = false,
  }) async {
    try {
      final response = await _dio.request<dynamic>(
        path,
        data: data,
        queryParameters: queryParameters,
        options: Options(method: method, extra: {'public': public}),
      );
      return response.data;
    } on DioException catch (e) {
      throw _toApiException(e);
    }
  }

  Future<void> _onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    final isPublic = options.extra['public'] == true;
    if (!isPublic) {
      final access = await _tokenStore.readAccess();
      if (access != null) {
        options.headers['Authorization'] = 'Bearer $access';
      }
    }
    handler.next(options);
  }

  Future<void> _onError(
    DioException err,
    ErrorInterceptorHandler handler,
  ) async {
    final options = err.requestOptions;
    final isPublic = options.extra['public'] == true;
    final alreadyRetried = options.extra['_retried'] == true;
    final apiError = _toApiException(err);
    final isUnauthenticated =
        err.response?.statusCode == 401 && apiError.code == 'UNAUTHENTICATED';

    if (isPublic || alreadyRetried || !isUnauthenticated) {
      handler.reject(err.copyWith(error: apiError));
      return;
    }

    try {
      await _ensureRefreshed();
    } on ApiException catch (refreshError) {
      handler.reject(err.copyWith(error: refreshError));
      return;
    }

    options.extra['_retried'] = true;
    try {
      final retried = await _dio.fetch<dynamic>(options);
      handler.resolve(retried);
    } on DioException catch (retryErr) {
      handler.reject(retryErr.copyWith(error: _toApiException(retryErr)));
    }
  }

  /// 진행 중인 리프레시가 있으면 그것을 기다리고, 없으면 새로 시작한다.
  Future<void> _ensureRefreshed() {
    final existing = _refreshFuture;
    if (existing != null) return existing;

    final future = _performRefresh();
    _refreshFuture = future;
    // `whenComplete`이 만드는 파생 Future는 아무도 await하지 않는다. 원본
    // `future`의 에러는 다른 곳(각 요청의 catch)에서 이미 처리되므로,
    // 이 파생 Future에 `ignore()`를 걸어 두 번째 "처리되지 않은 예외"로
    // 잡히는 것을 막는다.
    future.whenComplete(() {
      if (identical(_refreshFuture, future)) {
        _refreshFuture = null;
      }
    }).ignore();
    return future;
  }

  Future<void> _performRefresh() async {
    final refreshToken = await _tokenStore.readRefresh();
    if (refreshToken == null) {
      await _tokenStore.clear();
      _onSessionEnded?.call();
      throw ApiException(
        statusCode: 401,
        code: 'UNAUTHENTICATED',
        message: '리프레시 토큰이 없습니다.',
      );
    }

    try {
      final response = await _refreshDio.post<Map<String, dynamic>>(
        '/v1/auth/refresh',
        data: {'refresh_token': refreshToken},
      );
      final body = response.data!;
      await _tokenStore.save(
        access: body['access_token'] as String,
        refresh: body['refresh_token'] as String,
      );
    } on DioException catch (e) {
      final apiError = ApiException.fromDioException(e);
      // 요청이 백엔드에 닿지 못한 실패(연결·타임아웃, 게이트웨이의 502·503·504)는
      // 토큰이 아직 소모되지 않았을 가능성이 높다. 토큰을 남겨 두고, 사용자가 다음에
      // 직접 일으킨 요청에서 한 번 더 시도하게 한다. 여기서 자동으로 다시 보내지는 않는다.
      final reachedBackend = !apiError.isNetwork &&
          !_gatewayFailures.contains(apiError.statusCode);
      if (reachedBackend) {
        // 서버가 거절했거나(401·403, 재사용 감지 포함) 처리 중 실패했다(500 — 토큰이 이미
        // 소모됐을 수 있다). 이 기기의 토큰을 버리고 세션 종료를 알린다.
        await _tokenStore.clear();
        _onSessionEnded?.call();
      }
      throw apiError;
    }
  }

  ApiException _toApiException(DioException e) {
    final error = e.error;
    if (error is ApiException) return error;
    return ApiException.fromDioException(e);
  }
}
```

- [ ] **Step 4: 통과를 확인한다**

Run: `flutter test test/core/proxy && flutter analyze`
Expected: `All tests passed!` (12개), `No issues found!`

- [ ] **Step 5: 판별력을 확인한다**

`_ensureRefreshed` 의 `if (existing != null) return existing;` 한 줄을 잠깐 지우고 `flutter test test/core/proxy` 를 돌린다. `동시에 … 리프레시는 한 번만` 테스트가 실패해야 한다(갱신이 3번 나간다). 확인한 뒤 되돌린다. 실패하지 않으면 테스트가 단일 갱신을 지키지 못하는 것이니 테스트를 고친다.

- [ ] **Step 6: 커밋**

```bash
git add app/lib/core/proxy app/test/support app/test/core/proxy
git commit -m "feat(app): ApiClient — 갱신은 동시에 하나만, 실패한 갱신은 다시 보내지 않는다"
```

### Task 6: 세션 — 모델, 인증 API, 게이트웨이, 컨트롤러

**Files:**
- Create: `app/lib/features/auth/state/session.dart`, `session_gateway.dart`, `session_controller.dart`
- Create: `app/lib/features/auth/api/social_sign_in.dart`, `auth_api.dart`, `me_api.dart`
- Create: `app/lib/core/proxy/providers.dart`
- Test: `app/test/support/fake_session_gateway.dart`, `app/test/features/auth/session_models_test.dart`, `http_session_gateway_test.dart`, `session_controller_test.dart`, `session_ended_wiring_test.dart`

**Interfaces:**
- Consumes: `AppConfig`(Task 1), `ApiException`·`TokenStore`·`PrefsStore`(Task 4), `ApiClient`·`FakeHttpClientAdapter`(Task 5)
- Produces:
  - `ShopMembership {int shopId; String shopName; String role; bool get isOwner}` · `Me {int id; String displayName; String? profileImageUrl; List<String> identities; List<ShopMembership> shops}` — 둘 다 `fromJson(Map<String, dynamic>)`
  - `sealed class Session` → `SignedOut({bool sessionExpired = false})`, `SignedIn({required Me me, required int? selectedShopId})` + `ShopMembership? get selectedShop`, `copyWith`
  - `SocialCredential({required String provider, required String token, String? authorizationCode, String? nonce, String? displayName})` + `toJson()` (null 은 뺀다), `abstract class SocialSignIn { String get provider; Future<SocialCredential?> signIn(); Future<void> disconnect(); }` — `signIn()` 의 `null` 은 사용자가 취소한 것이다
  - `AuthTokens {String accessToken; String refreshToken; int? userId}` (toString 없음), `AuthApi(ApiClient)`: `socialLogin(SocialCredential) → AuthTokens`, `logout(String refreshToken)` — 둘 다 `public: true`
  - `MeApi(ApiClient).fetch() → Me`
  - `abstract class SessionGateway { restore() → Me?; signIn(SocialCredential) → Me; signOut(); refreshMe() → Me; readLastShopId() → int?; writeLastShopId(int) }`, `HttpSessionGateway`
  - 프로바이더: `appConfigProvider`, `tokenStoreProvider`, `prefsStoreProvider`, `sessionEndedSignalProvider`(`SessionEndedSignal { void Function()? listener; void fire(); }`), `apiClientProvider`, `sessionGatewayProvider`, `sessionControllerProvider`
  - `SessionController extends AsyncNotifier<Session>`: `signIn(SocialCredential)`, `signOut()`, `selectShop(int)`, `reloadMe()`, `replaceMe(Me)`, `endSession()`

동작 규칙
- `restore()`: 저장된 리프레시 토큰이 없으면 HTTP 를 부르지 않고 `null`. 있으면 `/v1/me`. `UNAUTHENTICATED` 면 토큰을 지우고 `null`. **네트워크 오류는 다시 던진다 — 토큰을 지우지 않는다**(스플래시가 "다시 시도"를 보여 준다).
- `signIn`: 토큰을 **저장한 뒤에** `/v1/me` 를 부른다. 실패하면 컨트롤러의 상태는 그대로(`SignedOut`)이고 예외가 호출한 화면으로 올라간다. 로딩 상태로 바꾸지 않는다(바꾸면 라우터가 스플래시로 튄다).
- `signOut`: 서버 로그아웃은 최선만 다한다(모든 오류를 삼킨다 — 오프라인에서도 로그아웃된다). 토큰과 기기 설정은 **언제나** 지운다.
- 고른 매장: 기억해 둔 매장이 아직 소속 목록에 있으면 그것, 아니고 매장이 하나면 그것, 그 밖에는 `null`. `reloadMe`·`replaceMe` 는 저장소가 아니라 **지금 고른 매장**을 후보로 다시 판정한다(고른 매장이 목록에서 사라졌으면 같은 규칙으로 떨어진다).
- `core/proxy` 는 `features/` 를 import 하지 않는다. 갱신 실패는 `SessionEndedSignal` 로 알리고, 컨트롤러가 `build()` 에서 `listener = endSession` 으로 받는다.
- Riverpod 3 은 실패한 프로바이더를 **자동으로 다시 만든다**(기본 재시도). 세션 복원이 조용히 되풀이되면 갱신이 여러 번 나갈 수 있다. 테스트가 "끄면 한 번, 안 끄면 여러 번"을 둘 다 보인다. 앱에서는 Task 7 의 `ProviderScope(retry: (_, __) => null)` 가 끈다.
- 기본 재시도를 켠 채 테스트를 끝내면 남은 타이머 때문에 테스트가 실패한다. 그런 테스트는 끝에서 `container.dispose()` 를 부른다.

- [ ] **Step 1: 테스트 지원과 실패하는 테스트를 쓴다**

`app/test/support/fake_session_gateway.dart`:
```dart
import 'package:chagocnote/features/auth/api/social_sign_in.dart';
import 'package:chagocnote/features/auth/state/session.dart';
import 'package:chagocnote/features/auth/state/session_gateway.dart';

/// 테스트 전용 메모리 기반 [SessionGateway]. 시나리오별로 필드를 채워 넣고,
/// 컨트롤러가 호출한 내용은 필드에 그대로 기록해 둔다.
class FakeSessionGateway implements SessionGateway {
  Me? meOnRestore;
  Object? restoreError;
  int? lastShopId;

  /// restore() 가 호출된 횟수. 재시도 여부를 세는 데 쓴다.
  int restoreCallCount = 0;

  Me? meOnSignIn;
  Object? signInError;

  /// signIn에 실제로 넘어온 자격 증명. 인자를 제대로 전달했는지 검증한다.
  SocialCredential? receivedCredential;

  Me? meOnRefresh;
  Object? refreshMeError;

  bool signOutCalled = false;
  int? writtenShopId;

  @override
  Future<Me?> restore() async {
    restoreCallCount++;
    if (restoreError != null) throw restoreError!;
    return meOnRestore;
  }

  @override
  Future<Me> signIn(SocialCredential credential) async {
    receivedCredential = credential;
    if (signInError != null) throw signInError!;
    return meOnSignIn!;
  }

  @override
  Future<void> signOut() async {
    signOutCalled = true;
  }

  @override
  Future<Me> refreshMe() async {
    if (refreshMeError != null) throw refreshMeError!;
    return meOnRefresh!;
  }

  @override
  Future<int?> readLastShopId() async => lastShopId;

  @override
  Future<void> writeLastShopId(int shopId) async {
    writtenShopId = shopId;
    lastShopId = shopId;
  }
}
```

`app/test/features/auth/session_models_test.dart`:
```dart
import 'package:chagocnote/features/auth/state/session.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('ShopMembership', () {
    test('서버가 주는 스네이크케이스 JSON을 그대로 읽는다', () {
      final shop = ShopMembership.fromJson({
        'shop_id': 7,
        'shop_name': 'Hiss Haus',
        'role': 'owner',
      });

      expect(shop.shopId, 7);
      expect(shop.shopName, 'Hiss Haus');
      expect(shop.role, 'owner');
    });

    test('role 이 owner 이면 isOwner 가 true 다', () {
      const owner = ShopMembership(shopId: 1, shopName: 'A', role: 'owner');
      const staff = ShopMembership(shopId: 2, shopName: 'B', role: 'staff');

      expect(owner.isOwner, isTrue);
      expect(staff.isOwner, isFalse);
    });
  });

  group('Me', () {
    test('서버가 주는 스네이크케이스 JSON을 그대로 읽는다', () {
      final me = Me.fromJson({
        'id': 42,
        'display_name': '민석',
        'profile_image_url': 'https://example.com/a.png',
        'identities': ['apple', 'kakao'],
        'shops': [
          {'shop_id': 1, 'shop_name': 'A매장', 'role': 'owner'},
        ],
      });

      expect(me.id, 42);
      expect(me.displayName, '민석');
      expect(me.profileImageUrl, 'https://example.com/a.png');
      expect(me.identities, ['apple', 'kakao']);
      expect(me.shops, hasLength(1));
      expect(me.shops.single.shopName, 'A매장');
    });

    test('profile_image_url 이 null 이어도 파싱된다', () {
      final me = Me.fromJson({
        'id': 1,
        'display_name': '민석',
        'profile_image_url': null,
        'identities': <String>[],
        'shops': <Map<String, dynamic>>[],
      });

      expect(me.profileImageUrl, isNull);
      expect(me.shops, isEmpty);
    });
  });

  group('SignedIn.selectedShop', () {
    const ownerA = ShopMembership(shopId: 1, shopName: 'A매장', role: 'owner');
    const staffB = ShopMembership(shopId: 2, shopName: 'B매장', role: 'staff');
    final me = Me(
      id: 1,
      displayName: '민석',
      profileImageUrl: null,
      identities: const ['apple'],
      shops: [ownerA, staffB],
    );

    test('selectedShopId 와 일치하는 매장을 돌려준다', () {
      final signedIn = SignedIn(me: me, selectedShopId: staffB.shopId);
      expect(signedIn.selectedShop, staffB);
    });

    test('selectedShopId 가 null 이면 null 이다', () {
      final signedIn = SignedIn(me: me, selectedShopId: null);
      expect(signedIn.selectedShop, isNull);
    });

    test('selectedShopId 가 소속 목록에 없으면 null 이다', () {
      final signedIn = SignedIn(me: me, selectedShopId: 999);
      expect(signedIn.selectedShop, isNull);
    });
  });

  test('SignedOut 의 sessionExpired 기본값은 false 다', () {
    expect(const SignedOut().sessionExpired, isFalse);
    expect(const SignedOut(sessionExpired: true).sessionExpired, isTrue);
  });
}
```

`app/test/features/auth/http_session_gateway_test.dart`:
```dart
import 'dart:convert';
import 'dart:typed_data';

import 'package:chagocnote/core/error/api_exception.dart';
import 'package:chagocnote/core/proxy/api_client.dart';
import 'package:chagocnote/core/storage/prefs_store.dart';
import 'package:chagocnote/core/storage/token_store.dart';
import 'package:chagocnote/features/auth/api/auth_api.dart';
import 'package:chagocnote/features/auth/api/me_api.dart';
import 'package:chagocnote/features/auth/api/social_sign_in.dart';
import 'package:chagocnote/features/auth/state/session_gateway.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../support/fake_http_client_adapter.dart';

const _meJson = {
  'id': 1,
  'display_name': '민석',
  'profile_image_url': null,
  'identities': ['apple'],
  'shops': <Map<String, dynamic>>[],
};

void main() {
  group('restore', () {
    test('저장된 리프레시 토큰이 없으면 HTTP 호출 없이 null 을 반환한다', () async {
      final adapter = FakeHttpClientAdapter((options, body) {
        fail('토큰이 없는데 요청이 나갔다: ${options.path}');
      });
      final tokenStore = MemoryTokenStore();
      final gateway = _buildGateway(adapter: adapter, tokenStore: tokenStore);

      final me = await gateway.restore();

      expect(me, isNull);
      expect(adapter.requests, isEmpty);
    });

    test('토큰이 있으면 /v1/me 를 호출해 Me 를 반환한다', () async {
      final adapter = FakeHttpClientAdapter((options, body) {
        expect(options.path, '/v1/me');
        return const FakeResponse(statusCode: 200, data: _meJson);
      });
      final tokenStore = MemoryTokenStore()
        ..save(access: 'access-1', refresh: 'refresh-1');
      final gateway = _buildGateway(adapter: adapter, tokenStore: tokenStore);

      final me = await gateway.restore();

      expect(me?.displayName, '민석');
    });

    test('/v1/me 가 401, 리프레시도 401 이면 null 을 반환하고 토큰을 지운다', () async {
      final adapter = FakeHttpClientAdapter((options, body) {
        if (options.path == '/v1/auth/refresh') {
          return const FakeResponse(
            statusCode: 401,
            data: {'code': 'UNAUTHENTICATED', 'message': '리프레시 토큰 만료'},
          );
        }
        return const FakeResponse(
          statusCode: 401,
          data: {'code': 'UNAUTHENTICATED', 'message': '액세스 토큰 만료'},
        );
      });
      final tokenStore = MemoryTokenStore()
        ..save(access: 'expired', refresh: 'also-expired');
      final gateway = _buildGateway(adapter: adapter, tokenStore: tokenStore);

      final me = await gateway.restore();

      expect(me, isNull);
      expect(await tokenStore.readAccess(), isNull);
      expect(await tokenStore.readRefresh(), isNull);
    });

    test('연결 오류가 나면 NETWORK 예외를 다시 던지고 토큰은 그대로 둔다', () async {
      final adapter = FakeHttpClientAdapter((options, body) {
        throw DioException.connectionTimeout(
          timeout: const Duration(seconds: 5),
          requestOptions: options,
        );
      });
      final tokenStore = MemoryTokenStore()
        ..save(access: 'access-1', refresh: 'refresh-1');
      final gateway = _buildGateway(adapter: adapter, tokenStore: tokenStore);

      await expectLater(
        gateway.restore(),
        throwsA(isA<ApiException>().having((e) => e.code, 'code', 'NETWORK')),
      );
      expect(await tokenStore.readAccess(), 'access-1');
      expect(await tokenStore.readRefresh(), 'refresh-1');
    });
  });

  group('signIn', () {
    test(
      '토큰을 먼저 저장한 뒤 /v1/me 를 요청하고, '
      '/v1/auth/social 요청에는 인증 헤더가 없으며 빈 필드는 생략된다',
      () async {
        final adapter = FakeHttpClientAdapter((options, body) {
          if (options.path == '/v1/auth/social') {
            expect(options.headers.containsKey('Authorization'), isFalse);
            final payload = jsonDecode(utf8.decode(body!)) as Map;
            expect(payload.keys, {'provider', 'token'});
            expect(payload['provider'], 'apple');
            expect(payload['token'], 'id-token');
            return const FakeResponse(
              statusCode: 200,
              data: {
                'access_token': 'new-access',
                'refresh_token': 'new-refresh',
                'token_type': 'bearer',
                'expires_in': 3600,
                'user_id': 1,
                'is_new_user': false,
              },
            );
          }
          expect(options.path, '/v1/me');
          expect(options.headers['Authorization'], 'Bearer new-access');
          return const FakeResponse(statusCode: 200, data: _meJson);
        });
        final tokenStore = MemoryTokenStore();
        final gateway = _buildGateway(adapter: adapter, tokenStore: tokenStore);

        final me = await gateway.signIn(
          const SocialCredential(provider: 'apple', token: 'id-token'),
        );

        expect(me.displayName, '민석');
        expect(await tokenStore.readAccess(), 'new-access');
        expect(await tokenStore.readRefresh(), 'new-refresh');
      },
    );
  });

  group('signOut', () {
    test('저장된 리프레시 토큰으로 로그아웃을 호출하고 토큰·설정을 지운다', () async {
      Uint8List? logoutBody;
      final adapter = FakeHttpClientAdapter((options, body) {
        if (options.path == '/v1/auth/logout') {
          logoutBody = body;
        }
        return const FakeResponse(statusCode: 204);
      });
      final tokenStore = MemoryTokenStore()
        ..save(access: 'access-1', refresh: 'refresh-1');
      final prefsStore = MemoryPrefsStore()..writeLastShopId(9);
      final gateway = _buildGateway(
        adapter: adapter,
        tokenStore: tokenStore,
        prefsStore: prefsStore,
      );

      await gateway.signOut();

      expect(
        jsonDecode(utf8.decode(logoutBody!)),
        {'refresh_token': 'refresh-1'},
      );
      expect(await tokenStore.readAccess(), isNull);
      expect(await tokenStore.readRefresh(), isNull);
      expect(await prefsStore.readLastShopId(), isNull);
    });

    test('로그아웃 호출이 네트워크 오류로 실패해도 토큰·설정은 지워진다', () async {
      final adapter = FakeHttpClientAdapter((options, body) {
        throw DioException.connectionTimeout(
          timeout: const Duration(seconds: 5),
          requestOptions: options,
        );
      });
      final tokenStore = MemoryTokenStore()
        ..save(access: 'access-1', refresh: 'refresh-1');
      final prefsStore = MemoryPrefsStore()..writeLastShopId(9);
      final gateway = _buildGateway(
        adapter: adapter,
        tokenStore: tokenStore,
        prefsStore: prefsStore,
      );

      await gateway.signOut();

      expect(await tokenStore.readAccess(), isNull);
      expect(await tokenStore.readRefresh(), isNull);
      expect(await prefsStore.readLastShopId(), isNull);
    });
  });
}

HttpSessionGateway _buildGateway({
  required FakeHttpClientAdapter adapter,
  required TokenStore tokenStore,
  PrefsStore? prefsStore,
}) {
  final dio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final refreshDio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final client = ApiClient(tokenStore: tokenStore, dio: dio, refreshDio: refreshDio);
  return HttpSessionGateway(
    authApi: AuthApi(client),
    meApi: MeApi(client),
    tokenStore: tokenStore,
    prefsStore: prefsStore ?? MemoryPrefsStore(),
  );
}
```

`app/test/features/auth/session_controller_test.dart`:
```dart
import 'package:chagocnote/features/auth/api/social_sign_in.dart';
import 'package:chagocnote/features/auth/state/session.dart';
import 'package:chagocnote/features/auth/state/session_controller.dart';
import 'package:chagocnote/features/auth/state/session_gateway.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../support/fake_session_gateway.dart';

const _ownerA = ShopMembership(shopId: 1, shopName: 'A매장', role: 'owner');
const _staffB = ShopMembership(shopId: 2, shopName: 'B매장', role: 'staff');

Me _me({List<ShopMembership> shops = const [], String name = '민석'}) => Me(
      id: 1,
      displayName: name,
      profileImageUrl: null,
      identities: const ['apple'],
      shops: shops,
    );

ProviderContainer _containerWith(SessionGateway gateway) => ProviderContainer.test(
      retry: (retryCount, error) => null,
      overrides: [sessionGatewayProvider.overrideWithValue(gateway)],
    );

void main() {
  group('매장 선택 규칙 (복원)', () {
    test('복원할 세션이 없으면 SignedOut 이 된다', () async {
      final gateway = FakeSessionGateway()..meOnRestore = null;
      final container = _containerWith(gateway);

      final session = await container.read(sessionControllerProvider.future);

      expect(session, isA<SignedOut>());
      expect((session as SignedOut).sessionExpired, isFalse);
    });

    test('매장이 없는 사용자는 selectedShopId 가 null 인 SignedIn 이 된다', () async {
      final gateway = FakeSessionGateway()..meOnRestore = _me(shops: const []);
      final container = _containerWith(gateway);

      final session = await container.read(sessionControllerProvider.future);

      final signedIn = session as SignedIn;
      expect(signedIn.me.shops, isEmpty);
      expect(signedIn.selectedShopId, isNull);
    });

    test('매장이 정확히 하나면 자동으로 선택된다', () async {
      final gateway = FakeSessionGateway()
        ..meOnRestore = _me(shops: [_ownerA])
        ..lastShopId = null;
      final container = _containerWith(gateway);

      final session = await container.read(sessionControllerProvider.future);

      expect((session as SignedIn).selectedShopId, _ownerA.shopId);
    });

    test('기억해둔 매장 id 가 아직 소속 목록에 있으면 그걸 선택한다', () async {
      final gateway = FakeSessionGateway()
        ..meOnRestore = _me(shops: [_ownerA, _staffB])
        ..lastShopId = _staffB.shopId;
      final container = _containerWith(gateway);

      final session = await container.read(sessionControllerProvider.future);

      expect((session as SignedIn).selectedShopId, _staffB.shopId);
    });

    test('매장이 둘 이상인데 기억해둔 id 가 없거나 무효하면 선택하지 않는다', () async {
      final gateway = FakeSessionGateway()
        ..meOnRestore = _me(shops: [_ownerA, _staffB])
        ..lastShopId = 999;
      final container = _containerWith(gateway);

      final session = await container.read(sessionControllerProvider.future);

      expect((session as SignedIn).selectedShopId, isNull);
    });
  });

  group('signIn', () {
    test('성공하면 SignedIn 상태로 바뀌고 매장 선택 규칙이 적용된다', () async {
      final gateway = FakeSessionGateway()
        ..meOnRestore = null
        ..meOnSignIn = _me(shops: [_ownerA]);
      final container = _containerWith(gateway);
      await container.read(sessionControllerProvider.future);

      final notifier = container.read(sessionControllerProvider.notifier);
      const credential = SocialCredential(provider: 'apple', token: 't');
      await notifier.signIn(credential);

      expect(gateway.receivedCredential, credential);
      final state = container.read(sessionControllerProvider);
      expect((state.value as SignedIn).selectedShopId, _ownerA.shopId);
    });

    test('실패하면 상태는 그대로 SignedOut 이고 예외가 그대로 올라온다', () async {
      final gateway = FakeSessionGateway()
        ..meOnRestore = null
        ..signInError = Exception('로그인 실패');
      final container = _containerWith(gateway);
      await container.read(sessionControllerProvider.future);

      final notifier = container.read(sessionControllerProvider.notifier);
      await expectLater(
        notifier.signIn(const SocialCredential(provider: 'apple', token: 't')),
        throwsA(isA<Exception>()),
      );

      final state = container.read(sessionControllerProvider);
      expect(state.hasError, isFalse);
      expect(state.value, isA<SignedOut>());
    });
  });

  test('signOut 을 호출하면 게이트웨이의 signOut 을 부르고 SignedOut 이 된다', () async {
    final gateway = FakeSessionGateway()..meOnRestore = _me(shops: [_ownerA]);
    final container = _containerWith(gateway);
    await container.read(sessionControllerProvider.future);

    final notifier = container.read(sessionControllerProvider.notifier);
    await notifier.signOut();

    expect(gateway.signOutCalled, isTrue);
    expect(container.read(sessionControllerProvider).value, isA<SignedOut>());
  });

  group('selectShop', () {
    test('선택한 매장을 저장하고 상태를 갱신한다', () async {
      final gateway = FakeSessionGateway()
        ..meOnRestore = _me(shops: [_ownerA, _staffB])
        ..lastShopId = null;
      final container = _containerWith(gateway);
      await container.read(sessionControllerProvider.future);

      final notifier = container.read(sessionControllerProvider.notifier);
      await notifier.selectShop(_staffB.shopId);

      expect(gateway.writtenShopId, _staffB.shopId);
      final signedIn = container.read(sessionControllerProvider).value as SignedIn;
      expect(signedIn.selectedShopId, _staffB.shopId);
    });

    test('소속되지 않은 매장 id 는 무시한다', () async {
      final gateway = FakeSessionGateway()
        ..meOnRestore = _me(shops: [_ownerA])
        ..lastShopId = null;
      final container = _containerWith(gateway);
      await container.read(sessionControllerProvider.future);

      final notifier = container.read(sessionControllerProvider.notifier);
      await notifier.selectShop(999);

      expect(gateway.writtenShopId, isNull);
      final signedIn = container.read(sessionControllerProvider).value as SignedIn;
      expect(signedIn.selectedShopId, _ownerA.shopId);
    });
  });

  group('reloadMe', () {
    test('성공하면 me 를 갱신한다', () async {
      final gateway = FakeSessionGateway()
        ..meOnRestore = _me(shops: [_ownerA], name: '이전이름')
        ..meOnRefresh = _me(shops: [_ownerA], name: '새이름');
      final container = _containerWith(gateway);
      await container.read(sessionControllerProvider.future);

      final notifier = container.read(sessionControllerProvider.notifier);
      await notifier.reloadMe();

      final signedIn = container.read(sessionControllerProvider).value as SignedIn;
      expect(signedIn.me.displayName, '새이름');
    });

    test('선택된 매장이 사라졌으면 다시 규칙을 적용해 미선택으로 되돌린다', () async {
      final gateway = FakeSessionGateway()
        ..meOnRestore = _me(shops: [_ownerA, _staffB])
        ..lastShopId = _staffB.shopId;
      final container = _containerWith(gateway);
      await container.read(sessionControllerProvider.future);
      expect(
        (container.read(sessionControllerProvider).value as SignedIn).selectedShopId,
        _staffB.shopId,
      );

      // staffB 매장에서 빠졌다 — 이제 ownerA 하나뿐이라 자동 선택된다.
      gateway.meOnRefresh = _me(shops: [_ownerA]);
      final notifier = container.read(sessionControllerProvider.notifier);
      await notifier.reloadMe();

      final signedIn = container.read(sessionControllerProvider).value as SignedIn;
      expect(signedIn.selectedShopId, _ownerA.shopId);
    });

    test('실패하면 상태를 그대로 두고 예외를 다시 던진다', () async {
      final gateway = FakeSessionGateway()
        ..meOnRestore = _me(shops: [_ownerA])
        ..refreshMeError = Exception('갱신 실패');
      final container = _containerWith(gateway);
      await container.read(sessionControllerProvider.future);
      final before = container.read(sessionControllerProvider).value;

      final notifier = container.read(sessionControllerProvider.notifier);
      await expectLater(notifier.reloadMe(), throwsA(isA<Exception>()));

      expect(container.read(sessionControllerProvider).value, before);
    });
  });

  test('endSession 은 즉시 sessionExpired 가 true 인 SignedOut 으로 만든다', () async {
    final gateway = FakeSessionGateway()..meOnRestore = _me(shops: [_ownerA]);
    final container = _containerWith(gateway);
    await container.read(sessionControllerProvider.future);

    final notifier = container.read(sessionControllerProvider.notifier);
    notifier.endSession();

    final state = container.read(sessionControllerProvider).value as SignedOut;
    expect(state.sessionExpired, isTrue);
  });

  group('재시도 끄기', () {
    testWidgets(
      'ProviderContainer.test(retry: (_, __) => null) 이면 '
      'build() 가 실패해도 정확히 한 번만 호출된다',
      (tester) async {
        final gateway = FakeSessionGateway()..restoreError = Exception('복원 실패');
        final container = ProviderContainer.test(
          retry: (retryCount, error) => null,
          overrides: [sessionGatewayProvider.overrideWithValue(gateway)],
        );

        container.listen(sessionControllerProvider, (previous, next) {});
        expect(gateway.restoreCallCount, 1);

        await tester.pump(const Duration(seconds: 10));
        expect(gateway.restoreCallCount, 1);
      },
    );

    testWidgets(
      'retry 옵션 없이 기본값을 쓰면 build() 가 실패했을 때 여러 번 재시도된다',
      (tester) async {
        final gateway = FakeSessionGateway()..restoreError = Exception('복원 실패');
        final container = ProviderContainer.test(
          overrides: [sessionGatewayProvider.overrideWithValue(gateway)],
        );

        container.listen(sessionControllerProvider, (previous, next) {});
        expect(gateway.restoreCallCount, 1);

        // defaultRetry: 200ms * 2^n 지수 백오프.
        await tester.pump(const Duration(milliseconds: 250));
        expect(gateway.restoreCallCount, greaterThan(1));

        // defaultRetry 는 최대 10번까지 Timer 를 예약해 둔다. 테스트가
        // "펜딩 타이머 없음" 불변조건에 걸리지 않도록 명시적으로 정리한다.
        container.dispose();
      },
    );
  });
}
```

`app/test/features/auth/session_ended_wiring_test.dart`:
```dart
// `core/proxy`(ApiClient)가 `features/auth`를 몰라도 리프레시 실패를 세션
// 컨트롤러에 전달할 수 있는지를, 실제 프로바이더 그래프로 확인한다.
//
// `apiClientProvider`는 production 코드에서 `Dio`/`FakeHttpClientAdapter`를
// 주입할 자리가 없다(baseUrl만 받는다). 이 테스트만을 위해 새 프로바이더를
// 추가하기보다, 테스트에서 `apiClientProvider` 자체를 가짜 어댑터를 문
// `ApiClient`로 오버라이드하는 쪽이 더 단순하다 — production 코드는 그대로
// 두고, `onSessionEnded`는 실제 코드와 똑같이
// `ref.read(sessionEndedSignalProvider).fire`를 그대로 쓴다.
import 'package:chagocnote/core/error/api_exception.dart';
import 'package:chagocnote/core/proxy/api_client.dart';
import 'package:chagocnote/core/proxy/providers.dart';
import 'package:chagocnote/core/storage/prefs_store.dart';
import 'package:chagocnote/core/storage/token_store.dart';
import 'package:chagocnote/features/auth/state/session.dart';
import 'package:chagocnote/features/auth/state/session_controller.dart';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../support/fake_http_client_adapter.dart';

const _meJson = {
  'id': 1,
  'display_name': '민석',
  'profile_image_url': null,
  'identities': ['apple'],
  'shops': <Map<String, dynamic>>[],
};

void main() {
  test(
    '보호된 호출이 401 을 받고 리프레시도 401 이면 '
    '세션 컨트롤러가 SignedOut(sessionExpired: true) 로 끝난다',
    () async {
      final adapter = FakeHttpClientAdapter((options, body) {
        if (options.path == '/v1/me') {
          return const FakeResponse(statusCode: 200, data: _meJson);
        }
        if (options.path == '/v1/auth/refresh') {
          return const FakeResponse(
            statusCode: 401,
            data: {'code': 'UNAUTHENTICATED', 'message': '리프레시 토큰 만료'},
          );
        }
        if (options.path == '/protected-probe') {
          return const FakeResponse(
            statusCode: 401,
            data: {'code': 'UNAUTHENTICATED', 'message': '액세스 토큰 만료'},
          );
        }
        fail('예상하지 못한 경로: ${options.path}');
      });
      final tokenStore = MemoryTokenStore()
        ..save(access: 'expired', refresh: 'refresh-1');
      final dio = Dio(BaseOptions())..httpClientAdapter = adapter;
      final refreshDio = Dio(BaseOptions())..httpClientAdapter = adapter;

      final container = ProviderContainer.test(
        retry: (retryCount, error) => null,
        overrides: [
          tokenStoreProvider.overrideWithValue(tokenStore),
          prefsStoreProvider.overrideWithValue(MemoryPrefsStore()),
          apiClientProvider.overrideWith(
            (ref) => ApiClient(
              tokenStore: tokenStore,
              dio: dio,
              refreshDio: refreshDio,
              onSessionEnded: ref.read(sessionEndedSignalProvider).fire,
            ),
          ),
        ],
      );

      final initial = await container.read(sessionControllerProvider.future);
      expect(initial, isA<SignedIn>());

      final client = container.read(apiClientProvider);
      await expectLater(
        client.get('/protected-probe'),
        throwsA(isA<ApiException>()),
      );

      final state = container.read(sessionControllerProvider).value as SignedOut;
      expect(state.sessionExpired, isTrue);
    },
  );
}
```

- [ ] **Step 2: 실패를 확인한다**

Run: `flutter test test/features/auth`
Expected: FAIL — `Not found: 'package:chagocnote/features/auth/state/session.dart'`

- [ ] **Step 3: 구현한다**

`app/lib/features/auth/state/session.dart`:
```dart
/// 세션을 이루는 모델과 상태.
///
/// `fromJson`은 서버가 주는 스네이크케이스 키를 그대로 읽는다. 토큰은 이
/// 계층에 전혀 나타나지 않는다 — 토큰은 `TokenStore`가 별도로 관리한다.
/// 그래서 `toString`을 오버라이드하지 않아도 민감 정보가 로그에 찍히지
/// 않지만, 그래도 필드를 나열하는 `toString`은 두지 않는다.
class ShopMembership {
  const ShopMembership({
    required this.shopId,
    required this.shopName,
    required this.role,
  });

  factory ShopMembership.fromJson(Map<String, dynamic> json) =>
      ShopMembership(
        shopId: json['shop_id'] as int,
        shopName: json['shop_name'] as String,
        role: json['role'] as String,
      );

  final int shopId;
  final String shopName;

  /// 'owner' | 'staff'
  final String role;

  bool get isOwner => role == 'owner';
}

class Me {
  const Me({
    required this.id,
    required this.displayName,
    required this.profileImageUrl,
    required this.identities,
    required this.shops,
  });

  factory Me.fromJson(Map<String, dynamic> json) => Me(
        id: json['id'] as int,
        displayName: json['display_name'] as String,
        profileImageUrl: json['profile_image_url'] as String?,
        identities: (json['identities'] as List).cast<String>(),
        shops: (json['shops'] as List)
            .map((e) => ShopMembership.fromJson(e as Map<String, dynamic>))
            .toList(),
      );

  final int id;
  final String displayName;
  final String? profileImageUrl;
  final List<String> identities;
  final List<ShopMembership> shops;
}

/// 세션 자체의 상태. 로딩/에러는 `AsyncValue`가 감싸므로 여기서는
/// "로그아웃"과 "로그인"만 표현한다.
sealed class Session {
  const Session();
}

/// 로그아웃 상태. [sessionExpired]는 HTTP 계층이 리프레시 실패로 세션을
/// 강제 종료했을 때 true가 된다 — 로그인 화면은 이때 "보안을 위해 다시
/// 로그인해 주세요"를 보여준다.
class SignedOut extends Session {
  const SignedOut({this.sessionExpired = false});

  final bool sessionExpired;
}

class SignedIn extends Session {
  const SignedIn({required this.me, required this.selectedShopId});

  final Me me;
  final int? selectedShopId;

  ShopMembership? get selectedShop {
    for (final shop in me.shops) {
      if (shop.shopId == selectedShopId) return shop;
    }
    return null;
  }

  SignedIn copyWith({Me? me, int? selectedShopId}) => SignedIn(
        me: me ?? this.me,
        selectedShopId: selectedShopId ?? this.selectedShopId,
      );
}
```

`app/lib/features/auth/api/social_sign_in.dart`:
```dart
/// 소셜 로그인 공급자가 돌려주는 자격 증명.
///
/// `toJson`은 서버가 기대하는 스네이크케이스 키로 바꾸고, 값이 없는 필드는
/// 아예 생략한다(서버가 `null`과 "필드 없음"을 다르게 취급할 수 있어서).
class SocialCredential {
  const SocialCredential({
    required this.provider,
    required this.token,
    this.authorizationCode,
    this.nonce,
    this.displayName,
  });

  final String provider;
  final String token;
  final String? authorizationCode;
  final String? nonce;
  final String? displayName;

  Map<String, dynamic> toJson() => {
        'provider': provider,
        'token': token,
        if (authorizationCode != null) 'authorization_code': authorizationCode,
        if (nonce != null) 'nonce': nonce,
        if (displayName != null) 'display_name': displayName,
      };
}

/// 소셜 로그인 공급자 하나를 다루는 포트. 카카오/구글/애플 구현체는
/// 이 참조 프로젝트의 범위 밖이다(다음 작업에서 만든다).
abstract class SocialSignIn {
  String get provider;

  /// 사용자가 로그인을 취소하면 `null`을 반환한다.
  Future<SocialCredential?> signIn();

  Future<void> disconnect();
}
```

`app/lib/features/auth/api/auth_api.dart`:
```dart
import '../../../core/proxy/api_client.dart';
import 'social_sign_in.dart';

/// 로그인으로 받은 토큰 쌍. 토큰 값을 로그에 남기지 않도록 `toString`을
/// 오버라이드하지 않는다(기본 `toString`은 필드를 나열하지 않는다).
class AuthTokens {
  const AuthTokens({
    required this.accessToken,
    required this.refreshToken,
    required this.userId,
  });

  final String accessToken;
  final String refreshToken;
  final int? userId;
}

/// 로그인·로그아웃 전용 API. 둘 다 인증 토큰 없이(`public: true`) 호출한다 —
/// 로그인은 아직 토큰이 없고, 로그아웃은 만료된 토큰이어도 서버에 알려야 하기
/// 때문이다.
class AuthApi {
  AuthApi(this._client);

  final ApiClient _client;

  Future<AuthTokens> socialLogin(SocialCredential credential) async {
    final data = await _client.post(
      '/v1/auth/social',
      data: credential.toJson(),
      public: true,
    ) as Map<String, dynamic>;
    return AuthTokens(
      accessToken: data['access_token'] as String,
      refreshToken: data['refresh_token'] as String,
      userId: data['user_id'] as int?,
    );
  }

  Future<void> logout(String refreshToken) async {
    await _client.post(
      '/v1/auth/logout',
      data: {'refresh_token': refreshToken},
      public: true,
    );
  }
}
```

`app/lib/features/auth/api/me_api.dart`:
```dart
import '../../../core/proxy/api_client.dart';
import '../state/session.dart';

/// 로그인한 사용자 본인 정보를 가져오는 API.
class MeApi {
  MeApi(this._client);

  final ApiClient _client;

  Future<Me> fetch() async {
    final data = await _client.get('/v1/me') as Map<String, dynamic>;
    return Me.fromJson(data);
  }
}
```

`app/lib/features/auth/state/session_gateway.dart`:
```dart
import '../../../core/error/api_exception.dart';
import '../../../core/storage/prefs_store.dart';
import '../../../core/storage/token_store.dart';
import '../api/auth_api.dart';
import '../api/me_api.dart';
import '../api/social_sign_in.dart';
import 'session.dart';

/// 세션 컨트롤러가 실제 저장소/네트워크에 접근할 때 거치는 포트.
/// 프로덕션에서는 [HttpSessionGateway]로, 테스트에서는 메모리 기반 가짜
/// 구현으로 대체한다.
abstract class SessionGateway {
  Future<Me?> restore();
  Future<Me> signIn(SocialCredential credential);
  Future<void> signOut();
  Future<Me> refreshMe();
  Future<int?> readLastShopId();
  Future<void> writeLastShopId(int shopId);
}

/// [AuthApi]·[MeApi]·[TokenStore]·[PrefsStore]로 만든 실제 구현.
class HttpSessionGateway implements SessionGateway {
  HttpSessionGateway({
    required this._authApi,
    required this._meApi,
    required this._tokenStore,
    required this._prefsStore,
  });

  final AuthApi _authApi;
  final MeApi _meApi;
  final TokenStore _tokenStore;
  final PrefsStore _prefsStore;

  @override
  Future<Me?> restore() async {
    final refreshToken = await _tokenStore.readRefresh();
    if (refreshToken == null) return null;

    try {
      return await _meApi.fetch();
    } on ApiException catch (e) {
      if (e.code == 'UNAUTHENTICATED') {
        await _tokenStore.clear();
        return null;
      }
      // NETWORK 등 다른 오류는 그대로 전파한다. 스플래시 화면이 "다시 시도"를
      // 보여줄 수 있도록, 토큰은 지우지 않고 남겨 둔다.
      rethrow;
    }
  }

  @override
  Future<Me> signIn(SocialCredential credential) async {
    final tokens = await _authApi.socialLogin(credential);
    await _tokenStore.save(
      access: tokens.accessToken,
      refresh: tokens.refreshToken,
    );
    return _meApi.fetch();
  }

  @override
  Future<void> signOut() async {
    final refreshToken = await _tokenStore.readRefresh();
    if (refreshToken != null) {
      try {
        await _authApi.logout(refreshToken);
      } catch (_) {
        // 로그아웃은 오프라인에서도 되어야 한다 — 서버 통보 실패는 무시한다.
      }
    }
    await _tokenStore.clear();
    await _prefsStore.clear();
  }

  @override
  Future<Me> refreshMe() => _meApi.fetch();

  @override
  Future<int?> readLastShopId() => _prefsStore.readLastShopId();

  @override
  Future<void> writeLastShopId(int shopId) =>
      _prefsStore.writeLastShopId(shopId);
}
```

`app/lib/core/proxy/providers.dart`:
```dart
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../config/app_config.dart';
import '../storage/prefs_store.dart';
import '../storage/token_store.dart';
import 'api_client.dart';

final appConfigProvider = Provider<AppConfig>((ref) => AppConfig.fromEnvironment());

final tokenStoreProvider = Provider<TokenStore>((ref) => SecureTokenStore());

final prefsStoreProvider = Provider<PrefsStore>((ref) => SecurePrefsStore());

/// `core`가 `features`를 import하지 않고도 "세션이 끝났다"를 알릴 수 있게
/// 하는 신호. `ApiClient`가 리프레시 실패를 감지하면 [fire]를 부르고,
/// `features/auth`의 세션 컨트롤러가 [listener]를 등록해 받는다.
class SessionEndedSignal {
  void Function()? listener;

  void fire() => listener?.call();
}

final sessionEndedSignalProvider = Provider<SessionEndedSignal>(
  (ref) => SessionEndedSignal(),
);

final apiClientProvider = Provider<ApiClient>((ref) {
  final config = ref.watch(appConfigProvider);
  final tokenStore = ref.watch(tokenStoreProvider);
  final signal = ref.watch(sessionEndedSignalProvider);
  return ApiClient(
    tokenStore: tokenStore,
    baseUrl: config.apiBaseUrl,
    onSessionEnded: signal.fire,
  );
});
```

`app/lib/features/auth/state/session_controller.dart`:
```dart
import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/proxy/providers.dart';
import '../api/auth_api.dart';
import '../api/me_api.dart';
import '../api/social_sign_in.dart';
import 'session.dart';
import 'session_gateway.dart';

/// [SessionGateway] 구현을 주입하는 자리. 기본값은 실제 HTTP 구현이다 —
/// 테스트만 `overrideWithValue`로 가짜 게이트웨이를 꽂는다.
final sessionGatewayProvider = Provider<SessionGateway>((ref) {
  final client = ref.watch(apiClientProvider);
  return HttpSessionGateway(
    authApi: AuthApi(client),
    meApi: MeApi(client),
    tokenStore: ref.watch(tokenStoreProvider),
    prefsStore: ref.watch(prefsStoreProvider),
  );
});

/// 세션 상태를 소유하는 컨트롤러. 코드 생성 없이 plain `AsyncNotifier`로
/// 작성한다.
class SessionController extends AsyncNotifier<Session> {
  SessionGateway get _gateway => ref.read(sessionGatewayProvider);

  @override
  FutureOr<Session> build() async {
    // `core/proxy`가 `features`를 모르는 채로 "세션 종료"를 알릴 수 있도록,
    // 이 신호에 콜백을 등록한다. 컨트롤러가 폐기되면 등록을 해제한다.
    final signal = ref.read(sessionEndedSignalProvider);
    signal.listener = endSession;
    ref.onDispose(() => signal.listener = null);

    final me = await _gateway.restore();
    if (me == null) return const SignedOut();
    return _resolveFromStorage(me);
  }

  /// 부팅 시점처럼 "현재 상태"가 없을 때 쓰는 선택 규칙: 저장소에 기억해둔
  /// 매장 id를 우선 쓴다.
  Future<Session> _resolveFromStorage(Me me) async {
    final lastShopId = await _gateway.readLastShopId();
    return _resolveWith(me, lastShopId);
  }

  /// 매장 선택 규칙: [candidateShopId]가 아직 [me]의 소속 목록에 있으면 그것,
  /// 없고 매장이 정확히 하나면 그것, 그 외에는 미선택(null).
  Session _resolveWith(Me me, int? candidateShopId) {
    int? selectedShopId;
    if (candidateShopId != null &&
        me.shops.any((shop) => shop.shopId == candidateShopId)) {
      selectedShopId = candidateShopId;
    } else if (me.shops.length == 1) {
      selectedShopId = me.shops.single.shopId;
    }
    return SignedIn(me: me, selectedShopId: selectedShopId);
  }

  /// 로그인. 로딩 상태로 바꾸지 않고, 실패해도 상태를 바꾸지 않는다 —
  /// 로그인 화면이 예외를 받아 문구를 보여준다.
  Future<void> signIn(SocialCredential credential) async {
    final me = await _gateway.signIn(credential);
    state = AsyncData(await _resolveFromStorage(me));
  }

  /// 로그아웃. 게이트웨이의 `signOut`은 서버 통보 실패를 스스로 삼키므로
  /// 이 메서드는 던지지 않는다.
  Future<void> signOut() async {
    await _gateway.signOut();
    state = const AsyncData(SignedOut());
  }

  /// 매장 전환. [shopId]가 현재 소속 목록에 없으면 아무 일도 하지 않는다.
  Future<void> selectShop(int shopId) async {
    final current = state.value;
    if (current is! SignedIn) return;
    if (!current.me.shops.any((shop) => shop.shopId == shopId)) return;

    await _gateway.writeLastShopId(shopId);
    if (!ref.mounted) return;
    state = AsyncData(current.copyWith(selectedShopId: shopId));
  }

  /// 본인 정보를 다시 불러온다. 실패하면 상태를 그대로 두고 예외를 던진다.
  Future<void> reloadMe() async {
    final me = await _gateway.refreshMe();
    if (!ref.mounted) return;
    replaceMe(me);
  }

  /// HTTP 계층이 리프레시 실패를 감지했을 때 호출한다. 즉시 로그아웃 상태로
  /// 만든다.
  void endSession() {
    state = const AsyncData(SignedOut(sessionExpired: true));
  }

  /// 이미 가지고 있는 [Me]로 상태를 교체한다. `reloadMe`와 같은 선택 규칙을
  /// 쓰지만, 네트워크 호출이 없으므로 동기로 끝낼 수 있다: 현재 선택된
  /// 매장이 새 소속 목록에도 있으면 유지하고, 없으면 매장이 하나뿐일 때만
  /// 자동 선택하며, 그 외에는 미선택으로 되돌린다.
  void replaceMe(Me me) {
    final current = state.value;
    final previousSelectedShopId =
        current is SignedIn ? current.selectedShopId : null;
    state = AsyncData(_resolveWith(me, previousSelectedShopId));
  }
}

final sessionControllerProvider =
    AsyncNotifierProvider<SessionController, Session>(SessionController.new);
```

- [ ] **Step 4: 통과를 확인한다**

Run: `flutter test test/features/auth && flutter analyze`
Expected: `All tests passed!` (32개), `No issues found!`

- [ ] **Step 5: 커밋**

```bash
git add app/lib/features/auth app/lib/core/proxy/providers.dart app/test/features/auth app/test/support/fake_session_gateway.dart
git commit -m "feat(app): 세션 상태와 인증 API — 로그인 실패는 상태를 바꾸지 않고, 네트워크 오류는 토큰을 지우지 않는다"
```

### Task 7: 라우터 가드와 앱 진입점

**Files:**
- Create: `app/lib/core/router/app_router.dart`, `app/lib/core/router/placeholder_screens.dart`, `app/lib/app.dart`
- Modify: `app/lib/main.dart` (자리 표시 앱을 진짜 진입점으로 바꾼다)
- Delete: `app/test/smoke_test.dart`
- Test: `app/test/core/router/app_router_test.dart`

**Interfaces:**
- Consumes: `sessionControllerProvider`·`Session`·`SignedIn`·`SignedOut`(Task 6), `FakeSessionGateway`(Task 6)
- Produces:
  - `routerProvider` (`Provider<GoRouter>`), 경로: `/splash` `/login` `/invite` `/shops/select` `/home` `/settings` `/settings/members` `/settings/shop` `/settings/account` `/settings/account/withdraw`
  - `placeholder_screens.dart` 의 화면들과 `ScreenKeys` — **Task 8~13 이 진짜 화면으로 하나씩 바꾼다.** 바꿀 때는 `app_router.dart` 의 `builder` 와 import 만 고친다. `ScreenKeys` 의 키는 진짜 화면도 같은 값을 루트 위젯에 달아 이 작업의 테스트가 계속 통과하게 한다.
  - `class App extends ConsumerWidget` — `MaterialApp.router`

가드 규칙 (점검표 S3·S10)
| 세션 | 결과 |
|---|---|
| 불러오는 중 · 오류 | `/splash` 에 머문다(오류면 스플래시가 "다시 시도"를 보여 준다 — Task 8) |
| 로그아웃 | `/login` |
| 로그인 · 소속 0곳 | `/invite`. 단 `/settings/account`·`/settings/account/withdraw` 는 열린다(소속이 없어도 로그아웃·해제·탈퇴는 할 수 있어야 한다) |
| 로그인 · 소속 2곳 이상 · 고른 매장 없음 | `/shops/select`. 같은 두 경로는 열린다 |
| `/settings` `/settings/members` `/settings/shop` | 고른 매장이 있어야 한다. 없으면 `/home` |
| 로그인한 채 `/login`·`/splash` | `/home` |
| 로그인 · 소속 있음 · `/invite`·`/shops/select` | **그대로 둔다** — 다른 매장에 합류하거나 매장을 바꾸려고 설정에서 다시 연다. 그래서 **초대 수락과 매장 선택이 끝나면 화면이 직접 `context.go('/home')` 을 부른다**(Task 8 의 의무) |

구현 규칙 — 어기면 조용히 망가진다
- `redirect` 안에서는 `ref.read` 만 쓴다. `ref.watch` 를 쓰면 세션이 바뀔 때마다 `GoRouter` 가 새로 만들어져 내비게이션 스택이 초기화된다.
- 다시 평가하라는 신호는 `ref.listen` + `ChangeNotifier` 를 `refreshListenable` 에 물린다.
- `routerProvider` 는 평범한 `Provider` 다(autoDispose 아님). `ref.onDispose(router.dispose)` 를 빠뜨리지 않는다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`app/test/core/router/app_router_test.dart`:
```dart
import 'package:chagocnote/core/router/app_router.dart';
import 'package:chagocnote/core/router/placeholder_screens.dart';
import 'package:chagocnote/features/auth/state/session.dart';
import 'package:chagocnote/features/auth/state/session_controller.dart';
import 'package:chagocnote/features/auth/state/session_gateway.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../support/fake_session_gateway.dart';

const _ownerA = ShopMembership(shopId: 1, shopName: 'A매장', role: 'owner');
const _staffB = ShopMembership(shopId: 2, shopName: 'B매장', role: 'staff');

Me _me({List<ShopMembership> shops = const []}) => Me(
      id: 1,
      displayName: '민석',
      profileImageUrl: null,
      identities: const ['apple'],
      shops: shops,
    );

/// `MaterialApp.router`로 실제 앱과 같은 방식으로 라우터를 꽂는다.
/// [container]를 직접 받아서, 위젯 트리 바깥에서도 컨트롤러/라우터를
/// 조작할 수 있게 한다.
Widget _appWith(ProviderContainer container) {
  return UncontrolledProviderScope(
    container: container,
    child: Consumer(
      builder: (context, ref, _) {
        final router = ref.watch(routerProvider);
        return MaterialApp.router(routerConfig: router);
      },
    ),
  );
}

ProviderContainer _containerWith(SessionGateway gateway) =>
    ProviderContainer.test(
      retry: (retryCount, error) => null,
      overrides: [sessionGatewayProvider.overrideWithValue(gateway)],
    );

void main() {
  testWidgets('로그아웃 상태면 로그인 화면으로 간다', (tester) async {
    final gateway = FakeSessionGateway()..meOnRestore = null;
    final container = _containerWith(gateway);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.login), findsOneWidget);
  });

  testWidgets('매장이 없으면 초대 화면으로 간다', (tester) async {
    final gateway = FakeSessionGateway()..meOnRestore = _me(shops: const []);
    final container = _containerWith(gateway);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.invite), findsOneWidget);
  });

  testWidgets('매장이 하나면 바로 홈으로 간다', (tester) async {
    final gateway = FakeSessionGateway()..meOnRestore = _me(shops: [_ownerA]);
    final container = _containerWith(gateway);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.home), findsOneWidget);
  });

  testWidgets(
    '매장이 둘이고 선택된 게 없으면 매장 선택 화면으로 가고, 고른 뒤 홈으로 이동하면 그대로 머무른다',
    (tester) async {
      // `/shops/select`는 매장을 이미 가진 사용자도 다시 열 수 있어야 하므로
      // (설정에서 매장 전환) 선택만으로 라우터가 자동으로 홈으로 밀어내지
      // 않는다 — 실제 화면이라면 선택 버튼의 onPressed가 `/home`으로 이동
      // 시킬 것이다. 지금은 자리 표시 화면이라 그 이동을 직접 흉내낸다.
      final gateway = FakeSessionGateway()
        ..meOnRestore = _me(shops: [_ownerA, _staffB]);
      final container = _containerWith(gateway);

      await tester.pumpWidget(_appWith(container));
      await tester.pumpAndSettle();
      expect(find.byKey(ScreenKeys.shopSelect), findsOneWidget);

      await container
          .read(sessionControllerProvider.notifier)
          .selectShop(_staffB.shopId);
      container.read(routerProvider).go('/home');
      await tester.pumpAndSettle();

      expect(find.byKey(ScreenKeys.home), findsOneWidget);
      expect(gateway.writtenShopId, _staffB.shopId);
    },
  );

  testWidgets('기억해둔 매장 id 가 있으면 매장 선택 화면을 건너뛰고 홈으로 간다', (tester) async {
    final gateway = FakeSessionGateway()
      ..meOnRestore = _me(shops: [_ownerA, _staffB])
      ..lastShopId = _staffB.shopId;
    final container = _containerWith(gateway);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.home), findsOneWidget);
    expect(find.byKey(ScreenKeys.shopSelect), findsNothing);
  });

  testWidgets(
    '복원이 네트워크 오류로 실패하면 스플래시에 머무르고, '
    '다시 시도해서 성공하면 홈으로 간다',
    (tester) async {
      final gateway = FakeSessionGateway()
        ..restoreError = Exception('네트워크 오류');
      final container = _containerWith(gateway);

      await tester.pumpWidget(_appWith(container));
      await tester.pumpAndSettle();
      expect(find.byKey(ScreenKeys.splash), findsOneWidget);

      gateway.restoreError = null;
      gateway.meOnRestore = _me(shops: [_ownerA]);
      container.invalidate(sessionControllerProvider);
      await tester.pumpAndSettle();

      expect(find.byKey(ScreenKeys.home), findsOneWidget);
    },
  );

  testWidgets('홈에 있는 중 endSession 이 호출되면 로그인 화면으로 밀려난다', (tester) async {
    final gateway = FakeSessionGateway()..meOnRestore = _me(shops: [_ownerA]);
    final container = _containerWith(gateway);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();
    expect(find.byKey(ScreenKeys.home), findsOneWidget);

    container.read(sessionControllerProvider.notifier).endSession();
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.login), findsOneWidget);
  });

  testWidgets('로그아웃 상태로 /settings/members 딥링크를 열어도 로그인 화면으로 간다', (
    tester,
  ) async {
    final gateway = FakeSessionGateway()..meOnRestore = null;
    final container = _containerWith(gateway);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();
    expect(find.byKey(ScreenKeys.login), findsOneWidget);

    container.read(routerProvider).go('/settings/members');
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.login), findsOneWidget);
  });

  testWidgets('매장이 없는 사용자도 /settings/account 는 열 수 있다', (tester) async {
    final gateway = FakeSessionGateway()..meOnRestore = _me(shops: const []);
    final container = _containerWith(gateway);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();
    expect(find.byKey(ScreenKeys.invite), findsOneWidget);

    container.read(routerProvider).go('/settings/account');
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.settingsAccount), findsOneWidget);
  });

  testWidgets('매장이 있는 사용자는 /invite 를 열어도 홈으로 밀려나지 않는다', (tester) async {
    final gateway = FakeSessionGateway()..meOnRestore = _me(shops: [_ownerA]);
    final container = _containerWith(gateway);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();
    expect(find.byKey(ScreenKeys.home), findsOneWidget);

    container.read(routerProvider).go('/invite');
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.invite), findsOneWidget);
  });
}
```

Run: `flutter test test/core/router`
Expected: FAIL — `Not found: 'package:chagocnote/core/router/app_router.dart'`

- [ ] **Step 2: 구현한다**

`app/lib/core/router/placeholder_screens.dart`:
```dart
import 'package:flutter/material.dart';

/// 테스트/개발 중 화면을 식별하기 위한 키. 실제 화면이 생기면 이 파일 전체를
/// 걷어낸다.
class ScreenKeys {
  static const splash = Key('screen_splash');
  static const login = Key('screen_login');
  static const invite = Key('screen_invite');
  static const shopSelect = Key('screen_shop_select');
  static const home = Key('screen_home');
  static const settings = Key('screen_settings');
  static const settingsMembers = Key('screen_settings_members');
  static const settingsShop = Key('screen_settings_shop');
  static const settingsAccount = Key('screen_settings_account');
  static const settingsAccountWithdraw = Key('screen_settings_account_withdraw');
}

class _PlaceholderScreen extends StatelessWidget {
  const _PlaceholderScreen({required this.label, required this.screenKey});

  final String label;
  final Key screenKey;

  @override
  Widget build(BuildContext context) {
    return Scaffold(body: Center(child: Text(label, key: screenKey)));
  }
}

class SplashScreen extends StatelessWidget {
  const SplashScreen({super.key});

  @override
  Widget build(BuildContext context) =>
      const _PlaceholderScreen(label: 'splash', screenKey: ScreenKeys.splash);
}

class LoginScreen extends StatelessWidget {
  const LoginScreen({super.key});

  @override
  Widget build(BuildContext context) =>
      const _PlaceholderScreen(label: 'login', screenKey: ScreenKeys.login);
}

class InviteScreen extends StatelessWidget {
  const InviteScreen({super.key});

  @override
  Widget build(BuildContext context) =>
      const _PlaceholderScreen(label: 'invite', screenKey: ScreenKeys.invite);
}

class ShopSelectScreen extends StatelessWidget {
  const ShopSelectScreen({super.key});

  @override
  Widget build(BuildContext context) => const _PlaceholderScreen(
        label: 'shop_select',
        screenKey: ScreenKeys.shopSelect,
      );
}

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) =>
      const _PlaceholderScreen(label: 'home', screenKey: ScreenKeys.home);
}

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) => const _PlaceholderScreen(
        label: 'settings',
        screenKey: ScreenKeys.settings,
      );
}

class SettingsMembersScreen extends StatelessWidget {
  const SettingsMembersScreen({super.key});

  @override
  Widget build(BuildContext context) => const _PlaceholderScreen(
        label: 'settings_members',
        screenKey: ScreenKeys.settingsMembers,
      );
}

class SettingsShopScreen extends StatelessWidget {
  const SettingsShopScreen({super.key});

  @override
  Widget build(BuildContext context) => const _PlaceholderScreen(
        label: 'settings_shop',
        screenKey: ScreenKeys.settingsShop,
      );
}

class SettingsAccountScreen extends StatelessWidget {
  const SettingsAccountScreen({super.key});

  @override
  Widget build(BuildContext context) => const _PlaceholderScreen(
        label: 'settings_account',
        screenKey: ScreenKeys.settingsAccount,
      );
}

class SettingsAccountWithdrawScreen extends StatelessWidget {
  const SettingsAccountWithdrawScreen({super.key});

  @override
  Widget build(BuildContext context) => const _PlaceholderScreen(
        label: 'settings_account_withdraw',
        screenKey: ScreenKeys.settingsAccountWithdraw,
      );
}
```

`app/lib/core/router/app_router.dart`:
```dart
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/auth/state/session.dart';
import '../../features/auth/state/session_controller.dart';
import 'placeholder_screens.dart';

/// go_router의 `refreshListenable`은 평범한 [Listenable]을 요구한다. 세션이
/// 바뀔 때마다 이걸로 "redirect를 다시 평가해라"라고 알린다.
class _SessionRefreshListenable extends ChangeNotifier {
  void ping() => notifyListeners();
}

/// 매장이 선택되어 있어야만 열리는 경로.
const _shopScopedSettings = {'/settings', '/settings/members', '/settings/shop'};

/// 매장이 없어도(0-shop 사용자도) 열려 있어야 하는 계정 관련 경로 — 로그아웃,
/// 로그인 수단 해제, 탈퇴는 매장 유무와 무관하게 가능해야 한다.
const _accountExemptRoutes = {'/settings/account', '/settings/account/withdraw'};

/// 로그인/스플래시처럼 "머물 이유가 없는" 진입 화면. 로그인된 사용자가
/// 여기 있으면 홈으로 밀어낸다. `/invite`, `/shops/select`는 매장을 이미 가진
/// 사용자도 다시 열 수 있어야 하므로(다른 매장 합류, 매장 전환) 여기 넣지
/// 않는다.
const _entryOnlyRoutes = {'/login', '/splash'};

/// 라우터는 앱 생애주기 동안 단 한 번만 만들어져야 한다(그렇지 않으면
/// 내비게이션 스택이 매번 리셋된다). 그래서 `Provider`(autoDispose 아님)로
/// 제공하고, 세션이 바뀔 때는 redirect만 재평가되도록 `ref.listen` +
/// `refreshListenable` 조합을 쓴다. `redirect` 콜백 안에서 세션을 `ref.watch`
/// 하면 이 프로바이더 자체가 재실행되어 `GoRouter` 인스턴스가 새로 만들어지므로
/// 절대 하지 않는다.
final routerProvider = Provider<GoRouter>((ref) {
  final refresh = _SessionRefreshListenable();
  ref.listen(sessionControllerProvider, (previous, next) => refresh.ping());
  ref.onDispose(refresh.dispose);

  final router = GoRouter(
    initialLocation: '/splash',
    refreshListenable: refresh,
    redirect: (context, state) {
      final location = state.matchedLocation;
      final session = ref.read(sessionControllerProvider);

      if (session.isLoading || session.hasError) {
        return location == '/splash' ? null : '/splash';
      }

      return switch (session.value) {
        null || SignedOut() => location == '/login' ? null : '/login',
        SignedIn(:final me, :final selectedShopId) => _redirectSignedIn(
            location: location,
            shopCount: me.shops.length,
            selectedShopId: selectedShopId,
          ),
      };
    },
    routes: [
      GoRoute(path: '/splash', builder: (context, state) => const SplashScreen()),
      GoRoute(path: '/login', builder: (context, state) => const LoginScreen()),
      GoRoute(path: '/invite', builder: (context, state) => const InviteScreen()),
      GoRoute(
        path: '/shops/select',
        builder: (context, state) => const ShopSelectScreen(),
      ),
      GoRoute(path: '/home', builder: (context, state) => const HomeScreen()),
      GoRoute(
        path: '/settings',
        builder: (context, state) => const SettingsScreen(),
      ),
      GoRoute(
        path: '/settings/members',
        builder: (context, state) => const SettingsMembersScreen(),
      ),
      GoRoute(
        path: '/settings/shop',
        builder: (context, state) => const SettingsShopScreen(),
      ),
      GoRoute(
        path: '/settings/account',
        builder: (context, state) => const SettingsAccountScreen(),
      ),
      GoRoute(
        path: '/settings/account/withdraw',
        builder: (context, state) => const SettingsAccountWithdrawScreen(),
      ),
    ],
  );

  ref.onDispose(router.dispose);
  return router;
});

String? _redirectSignedIn({
  required String location,
  required int shopCount,
  required int? selectedShopId,
}) {
  if (shopCount == 0) {
    if (_accountExemptRoutes.contains(location)) return null;
    return location == '/invite' ? null : '/invite';
  }

  if (shopCount >= 2 && selectedShopId == null) {
    if (_accountExemptRoutes.contains(location)) return null;
    return location == '/shops/select' ? null : '/shops/select';
  }

  if (_shopScopedSettings.contains(location) && selectedShopId == null) {
    return '/home';
  }

  if (_entryOnlyRoutes.contains(location)) {
    return '/home';
  }

  return null;
}
```

`app/lib/app.dart`:
```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/router/app_router.dart';
import 'design/app_theme.dart';

class App extends ConsumerWidget {
  const App({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(routerProvider);
    return MaterialApp.router(
      routerConfig: router,
      title: '차곡노트',
      theme: appTheme(),
    );
  }
}
```

`app/lib/main.dart`:
```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'app.dart';
import 'design/bridge/glass_setup.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await initializeGlass();
  runApp(
    ProviderScope(
      // Riverpod 3의 기본 재시도를 끈다. 세션 복원 실패는 스플래시 화면이
      // "다시 시도" 버튼으로 사용자가 직접 재시도하게 해야지, 프레임워크가
      // 지수 백오프로 조용히 반복 시도하면 안 된다.
      retry: (retryCount, error) => null,
      child: wrapWithGlass(const App()),
    ),
  );
}
```

`app/test/smoke_test.dart` 를 지운다(`BootstrapApp` 이 사라졌다).

- [ ] **Step 3: 통과를 확인한다**

Run: `flutter test && flutter analyze`
Expected: `All tests passed!`, `No issues found!` — 라우터 테스트는 10개다.

- [ ] **Step 4: 판별력을 확인한다**

`app_router.dart` 의 `if (session.isLoading || session.hasError)` 에서 `|| session.hasError` 를 잠깐 지우고 `flutter test test/core/router` 를 돌린다. `복원이 네트워크 오류면 스플래시에 머문다` 계열 테스트가 실패해야 한다(오류 상태가 로그인 화면으로 떨어진다 — 그러면 네트워크가 끊겼을 뿐인 사용자가 로그아웃된 것처럼 보인다). 확인한 뒤 되돌린다.

- [ ] **Step 5: 커밋**

```bash
git add app/lib/core/router app/lib/app.dart app/lib/main.dart app/test/core/router
git rm -q app/test/smoke_test.dart
git commit -m "feat(app): 라우터 가드 — 세션에 따라 로그인·초대·매장 선택·홈으로 보낸다"
```

### Task 8: 인증 화면 — 스플래시, 로그인, 초대 코드 입력, 매장 선택

**Files:**
- Create: `app/lib/l10n/app_strings.dart`, `app/lib/core/router/screen_keys.dart`
- Create: `app/lib/features/auth/api/invite_api.dart`, `app/lib/features/auth/state/auth_providers.dart`, `app/lib/features/auth/state/social_sign_ins.dart`
- Create: `app/lib/features/auth/screens/splash_screen.dart`, `login_screen.dart`, `invite_code_screen.dart`, `shop_select_screen.dart`
- Modify: `app/lib/core/router/app_router.dart`, `app/lib/core/router/placeholder_screens.dart`, `app/test/core/router/app_router_test.dart`
- Test: `app/test/support/fake_social_sign_in.dart`, `app/test/features/auth/screens/{splash,login,invite_code,shop_select}_screen_test.dart`

**Interfaces:**
- Consumes: `sessionControllerProvider`·`SocialCredential`·`SocialSignIn`(Task 6), `routerProvider`·`ScreenKeys`(Task 7), `appConfigProvider`·`apiClientProvider`(Task 6), `messageFor`(Task 4), 디자인 위젯(Task 3), `AppBackground`·`appTheme`(Task 2)
- Produces:
  - `class AppStrings` — 화면 문구를 전부 여기에 모은다(이후 작업이 상수를 더한다)
  - `ScreenKeys` 가 `lib/core/router/screen_keys.dart` 로 옮겨진다. 진짜 화면은 루트 위젯에 같은 키를 달아 Task 7 의 라우터 테스트가 계속 통과한다.
  - `authApiProvider`, `meApiProvider`, `inviteApiProvider`, `socialSignInsProvider`(지금은 빈 목록 — Task 14 가 채운다)
  - `InviteApi(ApiClient).accept(String code) → InviteAccepted{shopId, shopName, role, memberId}`
  - 테스트 지원 `FakeSocialSignIn`

동작 규칙 (점검표 S3·S11)
- **개발용 로그인은 `appConfig.isDev` 일 때만 보인다.** 이름이 비면 요청을 보내지 않는다.
- 소셜 로그인의 `signIn()` 이 `null` 이면 사용자가 취소한 것이다 — 아무 요청도 보내지 않는다.
- 로그인 실패는 `messageFor` 로 보여 주고 로그인 화면에 머문다(세션 상태는 바뀌지 않는다 — Task 6).
- 세션이 `SignedOut(sessionExpired: true)` 면 "보안을 위해 다시 로그인해 주세요" 띠를 보여 준다.
- 초대 수락이 성공하면 **순서대로** `reloadMe()` → `selectShop(shopId)` → `context.go('/home')`. 매장 선택도 `selectShop` → `context.go('/home')`. 라우터는 이 두 화면에서 자동으로 홈으로 보내지 않는다(Task 7 의 규칙).
- 초대 수락이 401 을 받으면(그사이 탈퇴·정지된 계정) `ApiClient` 가 갱신을 **한 번** 시도하고, 그것도 401 이면 세션이 끝나 로그인 화면으로 간다. 따로 짤 것은 없지만 이 경로를 가짜 어댑터로 끝까지 테스트한다.
- 소속이 없는 유저의 초대 화면에는 "계정 설정"(→ `/settings/account`)과 "로그아웃"이 있다 — 소속이 없어도 탈퇴할 수 있어야 한다.
- 스플래시는 세션이 오류일 때 문구와 "다시 시도"(`ref.invalidate(sessionControllerProvider)`)를 보여 준다.

- [ ] **Step 1: 테스트 지원과 실패하는 테스트를 쓴다**

`app/test/core/router/app_router_test.dart` — 바꾼다:
```diff
--- a/test/core/router/app_router_test.dart
+++ b/test/core/router/app_router_test.dart
@@ -1,5 +1,5 @@
 import 'package:chagocnote/core/router/app_router.dart';
-import 'package:chagocnote/core/router/placeholder_screens.dart';
+import 'package:chagocnote/core/router/screen_keys.dart';
 import 'package:chagocnote/features/auth/state/session.dart';
 import 'package:chagocnote/features/auth/state/session_controller.dart';
 import 'package:chagocnote/features/auth/state/session_gateway.dart';
```

`app/test/features/auth/screens/invite_code_screen_test.dart`:
```dart
// 초대 코드 화면을 실제 라우터 + 가짜 HTTP 어댑터로 끝까지 검증한다.
// `sessionGatewayProvider`는 오버라이드하지 않는다 — 진짜 `HttpSessionGateway`가
// (가짜 어댑터를 문) `apiClientProvider` 위에서 그대로 동작하게 해서,
// 세션 복원·재시도·초대 수락이 전부 같은 HTTP 계층을 타는 실제 통합
// 경로를 검증한다.
import 'package:chagocnote/core/proxy/api_client.dart';
import 'package:chagocnote/core/proxy/providers.dart';
import 'package:chagocnote/core/router/app_router.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/core/storage/prefs_store.dart';
import 'package:chagocnote/core/storage/token_store.dart';
import 'package:chagocnote/design/app_theme.dart';
import 'package:chagocnote/design/bridge/glass_surface.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/fake_http_client_adapter.dart';

const _meNoShops = {
  'id': 1,
  'display_name': '민석',
  'profile_image_url': null,
  'identities': ['apple'],
  'shops': <Map<String, dynamic>>[],
};

const _meWithShop = {
  'id': 1,
  'display_name': '민석',
  'profile_image_url': null,
  'identities': ['apple'],
  'shops': [
    {'shop_id': 3, 'shop_name': 'Hiss Haus', 'role': 'staff'},
  ],
};

ProviderContainer _containerWith(FakeHttpClientAdapter adapter) {
  final tokenStore = MemoryTokenStore()..save(access: 'a', refresh: 'r');
  final dio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final refreshDio = Dio(BaseOptions())..httpClientAdapter = adapter;
  return ProviderContainer.test(
    retry: (retryCount, error) => null,
    overrides: [
      tokenStoreProvider.overrideWithValue(tokenStore),
      prefsStoreProvider.overrideWithValue(MemoryPrefsStore()),
      apiClientProvider.overrideWith(
        (ref) => ApiClient(
          tokenStore: tokenStore,
          dio: dio,
          refreshDio: refreshDio,
          onSessionEnded: ref.read(sessionEndedSignalProvider).fire,
        ),
      ),
    ],
  );
}

Widget _appWith(ProviderContainer container) {
  return UncontrolledProviderScope(
    container: container,
    child: Consumer(
      builder: (context, ref, _) {
        final router = ref.watch(routerProvider);
        return MaterialApp.router(
          routerConfig: router,
          theme: appTheme(),
          builder: (context, child) => GlassBridge(
            factory: const OpaqueSurfaceFactory(),
            child: child!,
          ),
        );
      },
    ),
  );
}

void main() {
  testWidgets(
    '성공하면 수락 → 본인 정보 재조회 → 매장 선택 순으로 부르고 홈으로 이동한다',
    (tester) async {
      var meCallCount = 0;
      final adapter = FakeHttpClientAdapter((options, body) {
        if (options.path == '/v1/me') {
          meCallCount++;
          return FakeResponse(
            statusCode: 200,
            data: meCallCount == 1 ? _meNoShops : _meWithShop,
          );
        }
        if (options.path == '/v1/invites/accept') {
          return const FakeResponse(
            statusCode: 200,
            data: {
              'shop_id': 3,
              'shop_name': 'Hiss Haus',
              'role': 'staff',
              'member_id': 21,
            },
          );
        }
        fail('예상하지 못한 경로: ${options.path}');
      });
      final container = _containerWith(adapter);
      addTearDown(container.dispose);

      await tester.pumpWidget(_appWith(container));
      await tester.pumpAndSettle();
      expect(find.byKey(ScreenKeys.invite), findsOneWidget);

      await tester.enterText(find.byType(TextField), 'ABC123');
      await tester.tap(find.text(AppStrings.inviteSubmit));
      await tester.pumpAndSettle();

      expect(find.byKey(ScreenKeys.home), findsOneWidget);
      final paths = adapter.requests.map((r) => r.path).toList();
      expect(paths, ['/v1/me', '/v1/invites/accept', '/v1/me']);
    },
  );

  testWidgets('INVITE_EXPIRED 면 문구를 보여주고 초대 화면에 머무른다', (tester) async {
    final adapter = FakeHttpClientAdapter((options, body) {
      if (options.path == '/v1/me') {
        return const FakeResponse(statusCode: 200, data: _meNoShops);
      }
      if (options.path == '/v1/invites/accept') {
        return const FakeResponse(
          statusCode: 400,
          data: {'code': 'INVITE_EXPIRED', 'message': '만료된 코드'},
        );
      }
      fail('예상하지 못한 경로: ${options.path}');
    });
    final container = _containerWith(adapter);
    addTearDown(container.dispose);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextField), 'EXPIRED1');
    await tester.tap(find.text(AppStrings.inviteSubmit));
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.invite), findsOneWidget);
    expect(find.text('만료된 초대 코드입니다. 새 코드를 받아 주세요.'), findsOneWidget);
  });

  testWidgets('빈 코드로 제출하면 요청 없이 검증만 한다', (tester) async {
    final adapter = FakeHttpClientAdapter((options, body) {
      if (options.path == '/v1/me') {
        return const FakeResponse(statusCode: 200, data: _meNoShops);
      }
      fail('예상하지 못한 경로: ${options.path}');
    });
    final container = _containerWith(adapter);
    addTearDown(container.dispose);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();

    await tester.tap(find.text(AppStrings.inviteSubmit));
    await tester.pump();

    expect(find.text(AppStrings.inviteCodeRequired), findsOneWidget);
    expect(
      adapter.requests.where((r) => r.path == '/v1/invites/accept'),
      isEmpty,
    );
  });

  testWidgets('수락이 401 이고 리프레시도 401 이면 로그인 화면으로 밀려난다', (tester) async {
    final adapter = FakeHttpClientAdapter((options, body) {
      if (options.path == '/v1/me') {
        return const FakeResponse(statusCode: 200, data: _meNoShops);
      }
      if (options.path == '/v1/invites/accept') {
        return const FakeResponse(
          statusCode: 401,
          data: {'code': 'UNAUTHENTICATED', 'message': '액세스 토큰 만료'},
        );
      }
      if (options.path == '/v1/auth/refresh') {
        return const FakeResponse(
          statusCode: 401,
          data: {'code': 'UNAUTHENTICATED', 'message': '리프레시 토큰 만료'},
        );
      }
      fail('예상하지 못한 경로: ${options.path}');
    });
    final container = _containerWith(adapter);
    addTearDown(container.dispose);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextField), 'ABC123');
    await tester.tap(find.text(AppStrings.inviteSubmit));
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.login), findsOneWidget);
  });
}
```

`app/test/features/auth/screens/login_screen_test.dart`:
```dart
import 'package:chagocnote/core/config/app_config.dart';
import 'package:chagocnote/core/error/api_exception.dart';
import 'package:chagocnote/core/proxy/providers.dart';
import 'package:chagocnote/design/app_theme.dart';
import 'package:chagocnote/design/bridge/glass_surface.dart';
import 'package:chagocnote/features/auth/api/social_sign_in.dart';
import 'package:chagocnote/features/auth/screens/login_screen.dart';
import 'package:chagocnote/features/auth/state/session.dart';
import 'package:chagocnote/features/auth/state/session_controller.dart';
import 'package:chagocnote/features/auth/state/session_gateway.dart';
import 'package:chagocnote/features/auth/state/social_sign_ins.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/fake_session_gateway.dart';
import '../../../support/fake_social_sign_in.dart';

const _prodConfig = AppConfig(apiBaseUrl: '', appEnv: 'prod');
const _devConfig = AppConfig(apiBaseUrl: '', appEnv: 'dev');

Me _me() => const Me(
      id: 1,
      displayName: '민석',
      profileImageUrl: null,
      identities: ['apple'],
      shops: [],
    );

ProviderContainer _containerWith({
  required SessionGateway gateway,
  List<FakeSocialSignIn> signIns = const [],
  AppConfig config = _prodConfig,
}) =>
    ProviderContainer.test(
      retry: (retryCount, error) => null,
      overrides: [
        sessionGatewayProvider.overrideWithValue(gateway),
        socialSignInsProvider.overrideWithValue(signIns),
        appConfigProvider.overrideWithValue(config),
      ],
    );

Widget _appWith(ProviderContainer container) {
  return UncontrolledProviderScope(
    container: container,
    child: MaterialApp(
      theme: appTheme(),
      home: const GlassBridge(
        factory: OpaqueSurfaceFactory(),
        child: LoginScreen(),
      ),
    ),
  );
}

void main() {
  testWidgets('appEnv 가 dev 가 아니면 개발용 로그인 버튼이 없다', (tester) async {
    final gateway = FakeSessionGateway()..meOnRestore = null;
    final container = _containerWith(gateway: gateway, config: _prodConfig);
    addTearDown(container.dispose);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();

    expect(find.text(AppStrings.devSignIn), findsNothing);
  });

  testWidgets(
    'appEnv 가 dev 면 개발용 로그인 버튼이 있고, 이름이 비어 있으면 요청 없이 검증만 한다',
    (tester) async {
      final gateway = FakeSessionGateway()..meOnRestore = null;
      final container = _containerWith(gateway: gateway, config: _devConfig);
      addTearDown(container.dispose);

      await tester.pumpWidget(_appWith(container));
      await tester.pumpAndSettle();

      expect(find.text(AppStrings.devSignIn), findsOneWidget);

      await tester.tap(find.text(AppStrings.devSignIn));
      await tester.pump();

      expect(find.text(AppStrings.devNameRequired), findsOneWidget);
      expect(gateway.receivedCredential, isNull);
    },
  );

  testWidgets('개발용 로그인은 이름을 dev 자격 증명으로 보낸다', (tester) async {
    final gateway = FakeSessionGateway()
      ..meOnRestore = null
      ..meOnSignIn = _me();
    final container = _containerWith(gateway: gateway, config: _devConfig);
    addTearDown(container.dispose);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextField), '민석');
    await tester.tap(find.text(AppStrings.devSignIn));
    await tester.pump();
    await tester.pump();

    expect(gateway.receivedCredential?.provider, 'dev');
    expect(gateway.receivedCredential?.token, '민석');
  });

  testWidgets('소셜 로그인을 취소하면(null) 요청이 나가지 않는다', (tester) async {
    final gateway = FakeSessionGateway()..meOnRestore = null;
    final kakao = FakeSocialSignIn('kakao')..credentialToReturn = null;
    final container = _containerWith(gateway: gateway, signIns: [kakao]);
    addTearDown(container.dispose);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();

    await tester.tap(find.text(AppStrings.continueWithKakao));
    await tester.pump();
    await tester.pump();

    expect(kakao.signInCallCount, 1);
    expect(gateway.receivedCredential, isNull);
  });

  testWidgets('소셜 로그인이 실패하면 문구를 보여주고 로그인 화면에 머무른다', (tester) async {
    final gateway = FakeSessionGateway()..meOnRestore = null;
    gateway.signInError = ApiException(
      statusCode: 400,
      code: 'PROVIDER_VERIFICATION_FAILED',
      message: '실패',
    );
    final kakao = FakeSocialSignIn('kakao')
      ..credentialToReturn = const SocialCredential(
        provider: 'kakao',
        token: 'tok',
      );
    final container = _containerWith(gateway: gateway, signIns: [kakao]);
    addTearDown(container.dispose);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();

    await tester.tap(find.text(AppStrings.continueWithKakao));
    await tester.pump();
    await tester.pump();

    expect(find.text('로그인 정보를 확인하지 못했습니다. 다시 시도해 주세요.'), findsOneWidget);
    expect(find.text(AppStrings.continueWithKakao), findsOneWidget);
  });

  testWidgets('세션이 만료되어 로그아웃되면 배너를 보여준다', (tester) async {
    final gateway = FakeSessionGateway()..meOnRestore = null;
    final container = _containerWith(gateway: gateway);
    addTearDown(container.dispose);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();
    expect(find.text(AppStrings.sessionExpiredBanner), findsNothing);

    container.read(sessionControllerProvider.notifier).endSession();
    await tester.pump();

    expect(find.text(AppStrings.sessionExpiredBanner), findsOneWidget);
  });
}
```

`app/test/features/auth/screens/shop_select_screen_test.dart`:
```dart
import 'package:chagocnote/core/router/app_router.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/design/app_theme.dart';
import 'package:chagocnote/design/bridge/glass_surface.dart';
import 'package:chagocnote/features/auth/state/session.dart';
import 'package:chagocnote/features/auth/state/session_controller.dart';
import 'package:chagocnote/features/auth/state/session_gateway.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/fake_session_gateway.dart';

const _ownerA = ShopMembership(shopId: 1, shopName: 'Hiss Haus', role: 'owner');
const _staffB = ShopMembership(shopId: 2, shopName: 'B매장', role: 'staff');

Me _me() => const Me(
      id: 1,
      displayName: '민석',
      profileImageUrl: null,
      identities: ['apple'],
      shops: [_ownerA, _staffB],
    );

ProviderContainer _containerWith(SessionGateway gateway) =>
    ProviderContainer.test(
      retry: (retryCount, error) => null,
      overrides: [sessionGatewayProvider.overrideWithValue(gateway)],
    );

Widget _appWith(ProviderContainer container) {
  return UncontrolledProviderScope(
    container: container,
    child: Consumer(
      builder: (context, ref, _) {
        final router = ref.watch(routerProvider);
        return MaterialApp.router(
          routerConfig: router,
          theme: appTheme(),
          builder: (context, child) => GlassBridge(
            factory: const OpaqueSurfaceFactory(),
            child: child!,
          ),
        );
      },
    ),
  );
}

void main() {
  testWidgets('매장 이름과 역할 칩을 보여준다', (tester) async {
    final gateway = FakeSessionGateway()..meOnRestore = _me();
    final container = _containerWith(gateway);
    addTearDown(container.dispose);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.shopSelect), findsOneWidget);
    expect(find.text('Hiss Haus'), findsOneWidget);
    expect(find.text('B매장'), findsOneWidget);
    expect(find.text(AppStrings.roleOwner), findsOneWidget);
    expect(find.text(AppStrings.roleStaff), findsOneWidget);
  });

  testWidgets('매장을 고르면 선택 저장 후 홈으로 이동한다', (tester) async {
    final gateway = FakeSessionGateway()..meOnRestore = _me();
    final container = _containerWith(gateway);
    addTearDown(container.dispose);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();

    await tester.tap(find.text('B매장'));
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.home), findsOneWidget);
    expect(gateway.writtenShopId, _staffB.shopId);
  });
}
```

`app/test/features/auth/screens/splash_screen_test.dart`:
```dart
import 'package:chagocnote/design/app_theme.dart';
import 'package:chagocnote/design/bridge/glass_surface.dart';
import 'package:chagocnote/features/auth/screens/splash_screen.dart';
import 'package:chagocnote/features/auth/state/session_controller.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/fake_session_gateway.dart';

Widget _appWith(ProviderContainer container) {
  return UncontrolledProviderScope(
    container: container,
    child: MaterialApp(
      theme: appTheme(),
      home: const GlassBridge(
        factory: OpaqueSurfaceFactory(),
        child: SplashScreen(),
      ),
    ),
  );
}

void main() {
  testWidgets('복원이 실패하면 문구와 다시 시도 버튼을 보여주고, 누르면 다시 시도한다', (tester) async {
    final gateway = FakeSessionGateway()..restoreError = Exception('네트워크 오류');
    final container = ProviderContainer.test(
      retry: (retryCount, error) => null,
      overrides: [sessionGatewayProvider.overrideWithValue(gateway)],
    );
    addTearDown(container.dispose);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();

    expect(find.text('문제가 생겼습니다. 잠시 뒤에 다시 시도해 주세요.'), findsOneWidget);
    expect(gateway.restoreCallCount, 1);

    gateway.restoreError = null;
    await tester.tap(find.text('다시 시도'));
    // 재시도 뒤 상태는 로딩(스피너)으로 끝없이 애니메이션되므로
    // pumpAndSettle 대신 고정 프레임만 진행한다.
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    expect(gateway.restoreCallCount, 2);
  });
}
```

`app/test/support/fake_social_sign_in.dart`:
```dart
import 'package:chagocnote/features/auth/api/social_sign_in.dart';

/// 테스트 전용 [SocialSignIn]. `signIn()`이 몇 번 호출됐는지와, 무엇을
/// 돌려줄지(취소=null, 성공=credential, 실패=예외)를 필드로 기록·조작한다.
class FakeSocialSignIn implements SocialSignIn {
  FakeSocialSignIn(this.provider);

  @override
  final String provider;

  int signInCallCount = 0;
  SocialCredential? credentialToReturn;
  Object? signInError;

  @override
  Future<SocialCredential?> signIn() async {
    signInCallCount++;
    if (signInError != null) throw signInError!;
    return credentialToReturn;
  }

  @override
  Future<void> disconnect() async {}
}
```

Run: `flutter test test/features/auth/screens`
Expected: FAIL — 화면 파일이 없다.

- [ ] **Step 2: 구현한다**

`app/lib/core/router/app_router.dart` — 바꾼다:
```diff
--- a/lib/core/router/app_router.dart
+++ b/lib/core/router/app_router.dart
@@ -2,6 +2,10 @@ import 'package:flutter/foundation.dart';
 import 'package:flutter_riverpod/flutter_riverpod.dart';
 import 'package:go_router/go_router.dart';
 
+import '../../features/auth/screens/invite_code_screen.dart';
+import '../../features/auth/screens/login_screen.dart';
+import '../../features/auth/screens/shop_select_screen.dart';
+import '../../features/auth/screens/splash_screen.dart';
 import '../../features/auth/state/session.dart';
 import '../../features/auth/state/session_controller.dart';
 import 'placeholder_screens.dart';
@@ -59,7 +63,7 @@ final routerProvider = Provider<GoRouter>((ref) {
     routes: [
       GoRoute(path: '/splash', builder: (context, state) => const SplashScreen()),
       GoRoute(path: '/login', builder: (context, state) => const LoginScreen()),
-      GoRoute(path: '/invite', builder: (context, state) => const InviteScreen()),
+      GoRoute(path: '/invite', builder: (context, state) => const InviteCodeScreen()),
       GoRoute(
         path: '/shops/select',
         builder: (context, state) => const ShopSelectScreen(),
```

`app/lib/core/router/placeholder_screens.dart` — 바꾼다:
```diff
--- a/lib/core/router/placeholder_screens.dart
+++ b/lib/core/router/placeholder_screens.dart
@@ -1,20 +1,9 @@
 import 'package:flutter/material.dart';
 
-/// 테스트/개발 중 화면을 식별하기 위한 키. 실제 화면이 생기면 이 파일 전체를
-/// 걷어낸다.
-class ScreenKeys {
-  static const splash = Key('screen_splash');
-  static const login = Key('screen_login');
-  static const invite = Key('screen_invite');
-  static const shopSelect = Key('screen_shop_select');
-  static const home = Key('screen_home');
-  static const settings = Key('screen_settings');
-  static const settingsMembers = Key('screen_settings_members');
-  static const settingsShop = Key('screen_settings_shop');
-  static const settingsAccount = Key('screen_settings_account');
-  static const settingsAccountWithdraw = Key('screen_settings_account_withdraw');
-}
+import 'screen_keys.dart';
 
+/// 테스트/개발 중 화면을 식별하기 위한 자리 표시 화면. 실제 화면이 생기면
+/// 이 파일에서 하나씩 걷어낸다.
 class _PlaceholderScreen extends StatelessWidget {
   const _PlaceholderScreen({required this.label, required this.screenKey});
 
@@ -27,40 +16,6 @@ class _PlaceholderScreen extends StatelessWidget {
   }
 }
 
-class SplashScreen extends StatelessWidget {
-  const SplashScreen({super.key});
-
-  @override
-  Widget build(BuildContext context) =>
-      const _PlaceholderScreen(label: 'splash', screenKey: ScreenKeys.splash);
-}
-
-class LoginScreen extends StatelessWidget {
-  const LoginScreen({super.key});
-
-  @override
-  Widget build(BuildContext context) =>
-      const _PlaceholderScreen(label: 'login', screenKey: ScreenKeys.login);
-}
-
-class InviteScreen extends StatelessWidget {
-  const InviteScreen({super.key});
-
-  @override
-  Widget build(BuildContext context) =>
-      const _PlaceholderScreen(label: 'invite', screenKey: ScreenKeys.invite);
-}
-
-class ShopSelectScreen extends StatelessWidget {
-  const ShopSelectScreen({super.key});
-
-  @override
-  Widget build(BuildContext context) => const _PlaceholderScreen(
-        label: 'shop_select',
-        screenKey: ScreenKeys.shopSelect,
-      );
-}
-
 class HomeScreen extends StatelessWidget {
   const HomeScreen({super.key});
 
```

`app/lib/core/router/screen_keys.dart`:
```dart
import 'package:flutter/material.dart';

/// 라우터가 어떤 화면에 도달했는지 테스트에서 식별하기 위한 키. 실제 화면의
/// 루트 위젯이 이 키를 갖는다(자리 표시 화면이었을 때와 동일한 키를 유지).
class ScreenKeys {
  static const splash = Key('screen_splash');
  static const login = Key('screen_login');
  static const invite = Key('screen_invite');
  static const shopSelect = Key('screen_shop_select');
  static const home = Key('screen_home');
  static const settings = Key('screen_settings');
  static const settingsMembers = Key('screen_settings_members');
  static const settingsShop = Key('screen_settings_shop');
  static const settingsAccount = Key('screen_settings_account');
  static const settingsAccountWithdraw = Key('screen_settings_account_withdraw');
}
```

`app/lib/features/auth/api/invite_api.dart`:
```dart
import '../../../core/proxy/api_client.dart';

/// 초대 코드 수락 결과.
class InviteAccepted {
  const InviteAccepted({
    required this.shopId,
    required this.shopName,
    required this.role,
    required this.memberId,
  });

  factory InviteAccepted.fromJson(Map<String, dynamic> json) =>
      InviteAccepted(
        shopId: json['shop_id'] as int,
        shopName: json['shop_name'] as String,
        role: json['role'] as String,
        memberId: json['member_id'] as int,
      );

  final int shopId;
  final String shopName;
  final String role;
  final int memberId;
}

/// 초대 코드 수락 API.
class InviteApi {
  InviteApi(this._client);

  final ApiClient _client;

  Future<InviteAccepted> accept(String code) async {
    final data = await _client.post(
      '/v1/invites/accept',
      data: {'code': code},
    ) as Map<String, dynamic>;
    return InviteAccepted.fromJson(data);
  }
}
```

`app/lib/features/auth/screens/invite_code_screen.dart`:
```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/error/error_messages.dart';
import '../../../core/router/screen_keys.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_button.dart';
import '../../../l10n/app_strings.dart';
import '../state/auth_providers.dart';
import '../state/session.dart';
import '../state/session_controller.dart';

/// 초대 코드 입력 화면. 성공하면 본인 정보를 다시 불러와 해당 매장을 선택한
/// 뒤 홈으로 이동한다.
class InviteCodeScreen extends ConsumerStatefulWidget {
  const InviteCodeScreen({super.key});

  @override
  ConsumerState<InviteCodeScreen> createState() => _InviteCodeScreenState();
}

class _InviteCodeScreenState extends ConsumerState<InviteCodeScreen> {
  final _codeController = TextEditingController();
  bool _busy = false;
  String? _errorText;

  @override
  void dispose() {
    _codeController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final code = _codeController.text.trim();
    if (code.isEmpty) {
      setState(() => _errorText = AppStrings.inviteCodeRequired);
      return;
    }

    setState(() {
      _busy = true;
      _errorText = null;
    });
    try {
      final result = await ref.read(inviteApiProvider).accept(code);
      final controller = ref.read(sessionControllerProvider.notifier);
      await controller.reloadMe();
      await controller.selectShop(result.shopId);
      if (!mounted) return;
      context.go('/home');
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _busy = false;
        _errorText = messageFor(e);
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final session = ref.watch(sessionControllerProvider).value;
    final hasShops = session is SignedIn && session.me.shops.isNotEmpty;

    return Scaffold(
      key: ScreenKeys.invite,
      appBar: hasShops
          ? AppBar(
              backgroundColor: Colors.transparent,
              elevation: 0,
              leading: BackButton(
                onPressed: () {
                  if (context.canPop()) {
                    context.pop();
                  } else {
                    context.go('/settings');
                  }
                },
              ),
            )
          : null,
      body: AppBackground(
        child: SafeArea(
          child: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(AppSpacing.xl),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(AppStrings.inviteCodeLabel, style: AppTypography.titleKo),
                  const SizedBox(height: AppSpacing.lg),
                  TextField(
                    controller: _codeController,
                    decoration: InputDecoration(
                      labelText: AppStrings.inviteCodeLabel,
                      errorText: _errorText,
                    ),
                  ),
                  const SizedBox(height: AppSpacing.lg),
                  SizedBox(
                    width: double.infinity,
                    child: AppButton(
                      label: AppStrings.inviteSubmit,
                      filled: true,
                      busy: _busy,
                      onPressed: _busy ? null : _submit,
                    ),
                  ),
                  if (!hasShops) ...[
                    const SizedBox(height: AppSpacing.xxl),
                    AppButton(
                      label: AppStrings.accountSettings,
                      onPressed: () => context.go('/settings/account'),
                    ),
                    const SizedBox(height: AppSpacing.sm),
                    AppButton(
                      label: AppStrings.logout,
                      onPressed: () =>
                          ref.read(sessionControllerProvider.notifier).signOut(),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
```

`app/lib/features/auth/screens/login_screen.dart`:
```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/error/error_messages.dart';
import '../../../core/proxy/providers.dart';
import '../../../core/router/screen_keys.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_button.dart';
import '../../../l10n/app_strings.dart';
import '../api/social_sign_in.dart';
import '../state/session.dart';
import '../state/session_controller.dart';
import '../state/social_sign_ins.dart';

/// 로그인 화면. 소셜 로그인 공급자마다 버튼 하나, 개발 환경에서는 이름만
/// 넣는 개발용 로그인도 함께 보여준다.
class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _devNameController = TextEditingController();
  bool _busy = false;
  String? _errorText;
  String? _devNameError;

  @override
  void dispose() {
    _devNameController.dispose();
    super.dispose();
  }

  Future<void> _signInWith(SocialSignIn signIn) async {
    setState(() {
      _busy = true;
      _errorText = null;
    });
    try {
      final credential = await signIn.signIn();
      if (credential == null) {
        // 사용자가 취소했다 — 요청 없이 그대로 로그인 화면에 머무른다.
        if (mounted) setState(() => _busy = false);
        return;
      }
      await ref.read(sessionControllerProvider.notifier).signIn(credential);
      if (mounted) setState(() => _busy = false);
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _busy = false;
        _errorText = messageFor(e);
      });
    }
  }

  Future<void> _signInDev() async {
    final name = _devNameController.text.trim();
    if (name.isEmpty) {
      setState(() => _devNameError = AppStrings.devNameRequired);
      return;
    }
    setState(() {
      _devNameError = null;
      _busy = true;
      _errorText = null;
    });
    try {
      await ref.read(sessionControllerProvider.notifier).signIn(
            SocialCredential(provider: 'dev', token: name),
          );
      if (mounted) setState(() => _busy = false);
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _busy = false;
        _errorText = messageFor(e);
      });
    }
  }

  String _labelFor(String provider) => switch (provider) {
        'kakao' => AppStrings.continueWithKakao,
        'google' => AppStrings.continueWithGoogle,
        'apple' => AppStrings.continueWithApple,
        _ => provider,
      };

  @override
  Widget build(BuildContext context) {
    final signIns = ref.watch(socialSignInsProvider);
    final config = ref.watch(appConfigProvider);
    final session = ref.watch(sessionControllerProvider).value;
    final expired = session is SignedOut && session.sessionExpired;

    return Scaffold(
      key: ScreenKeys.login,
      body: AppBackground(
        child: SafeArea(
          child: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(AppSpacing.xl),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(AppStrings.appName, style: AppTypography.titleEn),
                  const SizedBox(height: AppSpacing.xxl),
                  if (expired) ...[
                    Text(
                      AppStrings.sessionExpiredBanner,
                      style: AppTypography.caption,
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: AppSpacing.lg),
                  ],
                  for (final signIn in signIns) ...[
                    SizedBox(
                      width: double.infinity,
                      child: AppButton(
                        label: _labelFor(signIn.provider),
                        filled: true,
                        busy: _busy,
                        onPressed: _busy ? null : () => _signInWith(signIn),
                      ),
                    ),
                    const SizedBox(height: AppSpacing.sm),
                  ],
                  if (config.isDev) ...[
                    const SizedBox(height: AppSpacing.lg),
                    TextField(
                      controller: _devNameController,
                      decoration: InputDecoration(
                        labelText: AppStrings.devNameLabel,
                        errorText: _devNameError,
                      ),
                    ),
                    const SizedBox(height: AppSpacing.sm),
                    SizedBox(
                      width: double.infinity,
                      child: AppButton(
                        label: AppStrings.devSignIn,
                        busy: _busy,
                        onPressed: _busy ? null : _signInDev,
                      ),
                    ),
                  ],
                  if (_errorText != null) ...[
                    const SizedBox(height: AppSpacing.lg),
                    Text(
                      _errorText!,
                      style: AppTypography.caption,
                      textAlign: TextAlign.center,
                    ),
                  ],
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
```

`app/lib/features/auth/screens/shop_select_screen.dart`:
```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/router/screen_keys.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_chip.dart';
import '../../../design/widgets/app_glass_card.dart';
import '../../../design/widgets/pressable.dart';
import '../../../l10n/app_strings.dart';
import '../state/session.dart';
import '../state/session_controller.dart';

/// 소속 매장 목록에서 하나를 골라 홈으로 들어가는 화면.
class ShopSelectScreen extends ConsumerWidget {
  const ShopSelectScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final session = ref.watch(sessionControllerProvider).value;
    final shops = session is SignedIn ? session.me.shops : const <ShopMembership>[];

    return Scaffold(
      key: ScreenKeys.shopSelect,
      body: AppBackground(
        child: SafeArea(
          child: ListView(
            padding: const EdgeInsets.all(AppSpacing.lg),
            children: [
              Text(AppStrings.selectShopTitle, style: AppTypography.titleKo),
              const SizedBox(height: AppSpacing.lg),
              for (final shop in shops)
                Padding(
                  padding: const EdgeInsets.only(bottom: AppSpacing.sm),
                  child: Pressable(
                    semanticLabel: shop.shopName,
                    onTap: () async {
                      await ref
                          .read(sessionControllerProvider.notifier)
                          .selectShop(shop.shopId);
                      if (context.mounted) context.go('/home');
                    },
                    child: AppGlassCard(
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(shop.shopName, style: AppTypography.body),
                          AppChip(
                            label: shop.isOwner
                                ? AppStrings.roleOwner
                                : AppStrings.roleStaff,
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}
```

`app/lib/features/auth/screens/splash_screen.dart`:
```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/error/error_messages.dart';
import '../../../core/router/screen_keys.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_button.dart';
import '../../../l10n/app_strings.dart';
import '../state/session_controller.dart';

/// 세션 복원 동안 보여주는 스플래시. 복원이 실패하면 오류 문구와 재시도
/// 버튼을 보여준다.
class SplashScreen extends ConsumerWidget {
  const SplashScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final session = ref.watch(sessionControllerProvider);

    return Scaffold(
      key: ScreenKeys.splash,
      body: AppBackground(
        child: Center(
          child: session.when(
            data: (_) => const CircularProgressIndicator(),
            loading: () => Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(AppStrings.appName, style: AppTypography.titleKo),
                const SizedBox(height: AppSpacing.lg),
                const CircularProgressIndicator(),
              ],
            ),
            error: (error, _) => Padding(
              padding: const EdgeInsets.all(AppSpacing.xl),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    messageFor(error),
                    style: AppTypography.body,
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: AppSpacing.lg),
                  AppButton(
                    label: AppStrings.retry,
                    onPressed: () => ref.invalidate(sessionControllerProvider),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
```

`app/lib/features/auth/state/auth_providers.dart`:
```dart
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/proxy/providers.dart';
import '../api/auth_api.dart';
import '../api/invite_api.dart';
import '../api/me_api.dart';

final authApiProvider = Provider<AuthApi>(
  (ref) => AuthApi(ref.watch(apiClientProvider)),
);

final meApiProvider = Provider<MeApi>(
  (ref) => MeApi(ref.watch(apiClientProvider)),
);

final inviteApiProvider = Provider<InviteApi>(
  (ref) => InviteApi(ref.watch(apiClientProvider)),
);
```

`app/lib/features/auth/state/social_sign_ins.dart`:
```dart
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/social_sign_in.dart';

/// 사용 가능한 소셜 로그인 구현체 목록. 실제 카카오/구글/애플 구현체는
/// 이후 슬라이스에서 채운다 — 지금은 빈 목록이다.
final socialSignInsProvider = Provider<List<SocialSignIn>>((ref) => const []);
```

`app/lib/l10n/app_strings.dart`:
```dart
/// 앱 전체에서 쓰는 사용자 노출 문자열. 전부 한국어다.
///
/// 화면은 이 파일의 상수만 쓰고, 문자열을 직접 쓰지 않는다. 오류 문구는
/// `messageFor`(`core/error/error_messages.dart`)를 대신 쓴다.
class AppStrings {
  const AppStrings._();

  static const appName = '차곡노트';
  static const retry = '다시 시도';

  // 로그인
  static const continueWithKakao = '카카오로 계속하기';
  static const continueWithGoogle = 'Google로 계속하기';
  static const continueWithApple = 'Apple로 계속하기';
  static const devNameLabel = '이름';
  static const devSignIn = '개발용 로그인';
  static const devNameRequired = '이름을 입력해 주세요.';
  static const sessionExpiredBanner = '보안을 위해 다시 로그인해 주세요.';

  // 초대 코드
  static const inviteCodeLabel = '초대 코드';
  static const inviteCodeRequired = '초대 코드를 입력해 주세요.';
  static const inviteSubmit = '참여하기';
  static const accountSettings = '계정 설정';
  static const logout = '로그아웃';

  // 매장 선택
  static const selectShopTitle = '매장 선택';
  static const roleOwner = '사장';
  static const roleStaff = '직원';
}
```

- [ ] **Step 3: 통과를 확인한다**

Run: `flutter test && flutter analyze`
Expected: `All tests passed!` — 이 작업의 새 테스트는 13개다. `No issues found!`

- [ ] **Step 4: 커밋**

```bash
git add app/lib app/test
git commit -m "feat(app): 스플래시·로그인·초대 코드·매장 선택 화면"
```

### Task 9: 홈 탭 셸

**Files:**
- Create: `app/lib/features/home/screens/home_shell.dart`, `app/lib/features/home/state/today_provider.dart`
- Modify: `app/lib/core/router/app_router.dart`, `app/lib/core/router/placeholder_screens.dart`, `app/lib/l10n/app_strings.dart`
- Test: `app/test/features/home/screens/home_shell_test.dart`, `home_shell_golden_test.dart`, `app/test/features/home/screens/goldens/home_shell.png`(생성물)

**Interfaces:**
- Consumes: `AppBigDate`·`AppGlassBar`·`AppFab`·`AppSheet`·`AppBackground`(Task 2·3), `sessionControllerProvider`(Task 6), `goldenFrame`·글꼴 로더(Task 2)
- Produces: `HomeShell`(`/home`), `todayProvider`(`Provider<DateTime>` — 테스트와 골든이 날짜를 고정한다)

규칙
- 머리말은 `AppBigDate` + 고른 매장 이름(한글 제목 글꼴) + 설정 버튼(의미 라벨 "설정", → `/settings`). 탭은 캘린더·고객·매출 셋이고 지금은 빈 상태 안내만 보여 준다(달력은 ③에서 만든다).
- `AppGlassBar` 는 `Scaffold.bottomNavigationBar` 에 두고 `extendBody: true` 를 켠다. 본문 `Column` 안에 두면 `AppFab` 이 탭바와 겹친다 — `Scaffold` 가 FAB 을 탭바 위로 띄워 준다.
- 글래스 아래로 스크롤되는 콘텐츠를 두지 않는다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`app/test/features/home/screens/home_shell_golden_test.dart`:
```dart
import 'package:chagocnote/design/app_theme.dart';
import 'package:chagocnote/design/bridge/glass_surface.dart';
import 'package:chagocnote/features/auth/state/session.dart';
import 'package:chagocnote/features/auth/state/session_controller.dart';
import 'package:chagocnote/features/home/screens/home_shell.dart';
import 'package:chagocnote/features/home/state/today_provider.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/fake_session_gateway.dart';

Me _meWithHissHaus() => const Me(
      id: 1,
      displayName: '민석',
      profileImageUrl: null,
      identities: ['apple'],
      shops: [ShopMembership(shopId: 1, shopName: 'Hiss Haus', role: 'owner')],
    );

void main() {
  testWidgets('홈 셸 골든 — 2026-09-22, Hiss Haus', (tester) async {
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final gateway = FakeSessionGateway()..meOnRestore = _meWithHissHaus();
    final container = ProviderContainer.test(
      retry: (retryCount, error) => null,
      overrides: [
        sessionGatewayProvider.overrideWithValue(gateway),
        todayProvider.overrideWithValue(DateTime(2026, 9, 22)),
      ],
    );
    addTearDown(container.dispose);

    // 세션이 해석될 때까지 미리 기다린다 — 골든 프레임 안에서는
    // 로딩(스피너) 프레임을 찍고 싶지 않다.
    await container.read(sessionControllerProvider.future);

    final key = GlobalKey();
    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: MaterialApp(
          theme: appTheme(),
          debugShowCheckedModeBanner: false,
          home: GlassBridge(
            factory: const OpaqueSurfaceFactory(),
            child: RepaintBoundary(key: key, child: const HomeShell()),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    await expectLater(
      find.byKey(key),
      matchesGoldenFile('goldens/home_shell.png'),
    );
  });
}
```

`app/test/features/home/screens/home_shell_test.dart`:
```dart
import 'package:chagocnote/core/router/app_router.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/design/app_theme.dart';
import 'package:chagocnote/design/bridge/glass_surface.dart';
import 'package:chagocnote/features/auth/state/session.dart';
import 'package:chagocnote/features/auth/state/session_controller.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/fake_session_gateway.dart';

Me _meWithHissHaus() => const Me(
      id: 1,
      displayName: '민석',
      profileImageUrl: null,
      identities: ['apple'],
      shops: [ShopMembership(shopId: 1, shopName: 'Hiss Haus', role: 'owner')],
    );

ProviderContainer _containerWith() {
  final gateway = FakeSessionGateway()..meOnRestore = _meWithHissHaus();
  return ProviderContainer.test(
    retry: (retryCount, error) => null,
    overrides: [sessionGatewayProvider.overrideWithValue(gateway)],
  );
}

Widget _appWith(ProviderContainer container) {
  return UncontrolledProviderScope(
    container: container,
    child: Consumer(
      builder: (context, ref, _) {
        final router = ref.watch(routerProvider);
        return MaterialApp.router(
          routerConfig: router,
          theme: appTheme(),
          builder: (context, child) => GlassBridge(
            factory: const OpaqueSurfaceFactory(),
            child: child!,
          ),
        );
      },
    ),
  );
}

void main() {
  testWidgets('매장 이름을 보여준다', (tester) async {
    final container = _containerWith();
    addTearDown(container.dispose);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.home), findsOneWidget);
    expect(find.text('Hiss Haus'), findsOneWidget);
  });

  testWidgets('탭을 바꾸면 본문이 바뀐다', (tester) async {
    final container = _containerWith();
    addTearDown(container.dispose);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();

    expect(find.text(AppStrings.calendarEmptyTitle), findsOneWidget);
    expect(find.text(AppStrings.comingSoonEmptyTitle), findsNothing);

    await tester.tap(find.text(AppStrings.tabCustomers));
    await tester.pumpAndSettle();

    expect(find.text(AppStrings.calendarEmptyTitle), findsNothing);
    expect(find.text(AppStrings.comingSoonEmptyTitle), findsOneWidget);

    await tester.tap(find.text(AppStrings.tabSales));
    await tester.pumpAndSettle();

    expect(find.text(AppStrings.comingSoonEmptyTitle), findsOneWidget);

    await tester.tap(find.text(AppStrings.tabCalendar));
    await tester.pumpAndSettle();

    expect(find.text(AppStrings.calendarEmptyTitle), findsOneWidget);
  });

  testWidgets('설정 버튼을 누르면 설정 화면으로 이동한다', (tester) async {
    final container = _containerWith();
    addTearDown(container.dispose);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();

    await tester.tap(find.byTooltip(AppStrings.settingsLabel));
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.settings), findsOneWidget);
  });

  testWidgets('FAB 을 누르면 준비 중 안내 시트가 뜬다', (tester) async {
    final container = _containerWith();
    addTearDown(container.dispose);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();

    await tester.tap(find.byIcon(Icons.add));
    await tester.pumpAndSettle();

    expect(find.text(AppStrings.comingSoonSheetText), findsOneWidget);
  });
}
```

Run: `flutter test test/features/home`
Expected: FAIL — `home_shell.dart` 가 없다.

- [ ] **Step 2: 구현한다**

`app/lib/core/router/app_router.dart` — 바꾼다:
```diff
--- a/lib/core/router/app_router.dart
+++ b/lib/core/router/app_router.dart
@@ -8,6 +8,7 @@ import '../../features/auth/screens/shop_select_screen.dart';
 import '../../features/auth/screens/splash_screen.dart';
 import '../../features/auth/state/session.dart';
 import '../../features/auth/state/session_controller.dart';
+import '../../features/home/screens/home_shell.dart';
 import 'placeholder_screens.dart';
 
 /// go_router의 `refreshListenable`은 평범한 [Listenable]을 요구한다. 세션이
@@ -68,7 +69,7 @@ final routerProvider = Provider<GoRouter>((ref) {
         path: '/shops/select',
         builder: (context, state) => const ShopSelectScreen(),
       ),
-      GoRoute(path: '/home', builder: (context, state) => const HomeScreen()),
+      GoRoute(path: '/home', builder: (context, state) => const HomeShell()),
       GoRoute(
         path: '/settings',
         builder: (context, state) => const SettingsScreen(),
```

`app/lib/core/router/placeholder_screens.dart` — 바꾼다:
```diff
--- a/lib/core/router/placeholder_screens.dart
+++ b/lib/core/router/placeholder_screens.dart
@@ -16,14 +16,6 @@ class _PlaceholderScreen extends StatelessWidget {
   }
 }
 
-class HomeScreen extends StatelessWidget {
-  const HomeScreen({super.key});
-
-  @override
-  Widget build(BuildContext context) =>
-      const _PlaceholderScreen(label: 'home', screenKey: ScreenKeys.home);
-}
-
 class SettingsScreen extends StatelessWidget {
   const SettingsScreen({super.key});
 
```

`app/lib/features/home/screens/home_shell.dart`:
```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/router/screen_keys.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_big_date.dart';
import '../../../design/widgets/app_fab.dart';
import '../../../design/widgets/app_glass_bar.dart';
import '../../../design/widgets/app_sheet.dart';
import '../../../l10n/app_strings.dart';
import '../../auth/state/session.dart';
import '../../auth/state/session_controller.dart';
import '../state/today_provider.dart';

/// 홈 화면. 헤더(날짜 + 매장 이름 + 설정), 탭별 본문, 하단 유리 탭바로
/// 이루어진다.
class HomeShell extends ConsumerStatefulWidget {
  const HomeShell({super.key});

  @override
  ConsumerState<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends ConsumerState<HomeShell> {
  int _tabIndex = 0;

  static const _items = [
    AppGlassBarItem(icon: Icons.calendar_today, label: AppStrings.tabCalendar),
    AppGlassBarItem(icon: Icons.people_outline, label: AppStrings.tabCustomers),
    AppGlassBarItem(icon: Icons.bar_chart_outlined, label: AppStrings.tabSales),
  ];

  void _openComingSoonSheet() {
    AppSheet.show<void>(
      context,
      builder: (context) => Padding(
        padding: const EdgeInsets.only(bottom: AppSpacing.lg),
        child: Text(
          AppStrings.comingSoonSheetText,
          style: AppTypography.body,
          textAlign: TextAlign.center,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final today = ref.watch(todayProvider);
    final session = ref.watch(sessionControllerProvider).value;
    final shopName =
        session is SignedIn ? session.selectedShop?.shopName ?? '' : '';

    return Scaffold(
      key: ScreenKeys.home,
      extendBody: true,
      floatingActionButton: AppFab(onPressed: _openComingSoonSheet),
      bottomNavigationBar: Padding(
        padding: const EdgeInsets.fromLTRB(
          AppSpacing.lg,
          0,
          AppSpacing.lg,
          AppSpacing.lg,
        ),
        child: SafeArea(
          top: false,
          child: AppGlassBar(
            items: _items,
            currentIndex: _tabIndex,
            onTap: (index) => setState(() => _tabIndex = index),
          ),
        ),
      ),
      body: AppBackground(
        child: SafeArea(
          bottom: false,
          child: Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(
                  AppSpacing.lg,
                  AppSpacing.md,
                  AppSpacing.sm,
                  AppSpacing.md,
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          AppBigDate(date: today),
                          const SizedBox(height: AppSpacing.sm),
                          Text(shopName, style: AppTypography.titleKo),
                        ],
                      ),
                    ),
                    IconButton(
                      onPressed: () => context.go('/settings'),
                      icon: const Icon(Icons.settings_outlined),
                      tooltip: AppStrings.settingsLabel,
                    ),
                  ],
                ),
              ),
              Expanded(child: _TabBody(index: _tabIndex)),
            ],
          ),
        ),
      ),
    );
  }
}

class _TabBody extends StatelessWidget {
  const _TabBody({required this.index});

  final int index;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: index == 0
          ? const _EmptyState(
              title: AppStrings.calendarEmptyTitle,
              caption: AppStrings.calendarEmptyCaption,
            )
          : const _EmptyState(title: AppStrings.comingSoonEmptyTitle),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState({required this.title, this.caption});

  final String title;
  final String? caption;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(AppSpacing.xl),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(title, style: AppTypography.body, textAlign: TextAlign.center),
          if (caption != null) ...[
            const SizedBox(height: AppSpacing.xs),
            Text(
              caption!,
              style: AppTypography.caption,
              textAlign: TextAlign.center,
            ),
          ],
        ],
      ),
    );
  }
}
```

`app/lib/features/home/state/today_provider.dart`:
```dart
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 오늘 날짜. 테스트·골든이 고정된 날짜로 오버라이드할 수 있도록
/// provider로 둔다.
final todayProvider = Provider<DateTime>((ref) => DateTime.now());
```

`app/lib/l10n/app_strings.dart` — 바꾼다:
```diff
--- a/lib/l10n/app_strings.dart
+++ b/lib/l10n/app_strings.dart
@@ -28,4 +28,14 @@ class AppStrings {
   static const selectShopTitle = '매장 선택';
   static const roleOwner = '사장';
   static const roleStaff = '직원';
+
+  // 홈 셸
+  static const settingsLabel = '설정';
+  static const tabCalendar = '캘린더';
+  static const tabCustomers = '고객';
+  static const tabSales = '매출';
+  static const calendarEmptyTitle = '아직 기록이 없습니다';
+  static const calendarEmptyCaption = '예약을 만들면 여기에서 모아 볼 수 있어요.';
+  static const comingSoonEmptyTitle = '준비 중입니다';
+  static const comingSoonSheetText = '예약과 기록은 다음 업데이트에서 만나요';
 }
```

- [ ] **Step 3: 골든을 만들고 눈으로 확인한다**

Run:
```bash
flutter test --update-goldens test/features/home
flutter test test/features/home
```
`test/features/home/screens/goldens/home_shell.png`(390×844, 2026-09-22, 매장 이름 "Hiss Haus")을 열어 본다. 확인할 것: 큰 세리프 "22" 와 기울인 "September"·"Tuesday" / 회백 그라데이션 바탕 / 아래 세 칸 탭바(선택된 "캘린더"만 검정) / 검정 원형 + 버튼이 **탭바와 겹치지 않는다** / 줄무늬(overflow) 없음 / 진짜 글리프와 아이콘. 기준 목업(`.superpowers/brainstorm/67059-1789889527/content/mono-tone.html`)과 나란히 놓고 다른 점을 보고서에 적는다.

- [ ] **Step 4: 전체 확인과 커밋**

Run: `flutter test && flutter analyze`
Expected: `All tests passed!` (새 테스트 5개), `No issues found!`

```bash
git add app/lib app/test
git commit -m "feat(app): 홈 탭 셸 — 큰 날짜 머리말, 글래스 탭바, + 버튼"
```

### Task 10: 설정 허브와 멤버 관리

**Files:**
- Create: `app/lib/features/shop/api/shop_api.dart`
- Create: `app/lib/features/shop/state/shop_providers.dart`, `shop_errors.dart`, `members_controller.dart`
- Create: `app/lib/features/shop/screens/settings_screen.dart`, `members_screen.dart`
- Modify: `app/lib/core/router/app_router.dart`, `placeholder_screens.dart`, `app/lib/l10n/app_strings.dart`, `app/test/support/fake_session_gateway.dart`(`refreshMeCallCount` 추가)
- Test: `app/test/features/shop/screens/settings_screen_test.dart`, `members_screen_test.dart`

**Interfaces:**
- Consumes: `apiClientProvider`·`sessionControllerProvider`·`SignedIn.selectedShop`(Task 6), 디자인 위젯, `messageFor`
- Produces:
  - `ShopApi(ApiClient)`: `members(int shopId) → List<ShopMember>`, `createInvite(int shopId) → CreatedInvite`, `changeRole(int shopId, int memberId, String role)`, `removeMember(int shopId, int memberId)`, `settings(int shopId) → ShopSettings`, `updateSettings(int shopId, {required String name, String? phone, String? address}) → ShopSettings`
  - 모델 `ShopMember{memberId, userId, displayName, profileImageUrl, role, joinedAt}`, `CreatedInvite{code, role, expiresAt}`(**`toString` 으로 코드를 내놓지 않는다**), `ShopSettings{shopId, name, businessType, phone, address, timezone}`
  - `shopApiProvider`, `Future<T> runShopScoped<T>(Ref ref, Future<T> Function() action)`, `membersControllerProvider`(`AsyncNotifierProvider.family` — 인자는 `shopId`)

동작 규칙 (점검표 S8·S9)
- **`NOT_A_MEMBER` 를 받으면 그 매장을 기기에서 지우지 않는다.** `runShopScoped` 가 `sessionController.reloadMe()` 를 부르고 오류를 다시 던진다. 내보내진 경우에는 새 `me` 에 매장이 없어 라우터가 내보내고, 강등된 경우에는 매장이 남아 그대로 머문다. 매장 범위의 컨트롤러는 **전부** 이 도우미를 거친다.
- 관리 UI(초대 코드 만들기, 역할 변경, 내보내기)는 `selectedShop.isOwner` 일 때만 보인다. 직원은 목록만 본다. **보안 경계는 서버의 403 이다 — 메뉴 숨김은 편의다.**
- 자기 자신의 행에는 동작 버튼을 두지 않는다. 역할 변경·내보내기가 **현재 유저**에게 영향을 주면(`userId == me.id`) `reloadMe()` 도 부른다.
- 초대 코드는 시트에 큰 세리프로 보여 주고 "복사"(클립보드)를 둔다. 코드를 로그에 남기지 않는다.
- Riverpod 3 의 family: `AsyncNotifierProvider.family<Notifier, Value, Arg>(Notifier.new)` — 인자는 노티파이어의 **생성자**로 들어가 필드에 저장되고 `build()` 는 인자를 받지 않는다(riverpod 3.4.3 소스로 확인).

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`app/test/features/shop/screens/members_screen_test.dart`:
```dart
// 멤버 화면을 실제 라우터로 검증한다. `sessionGatewayProvider`는
// `FakeSessionGateway`로(세션 복원·재조회를 직접 제어하기 위해), 매장 API는
// `apiClientProvider`를 가짜 어댑터로 문 진짜 `ShopApi`로 검증한다 — 두
// 계층이 서로 다른 경로(세션 vs 매장 API)를 타기 때문에 각각 가짜로
// 대체하는 쪽이 더 명확하다.
import 'package:chagocnote/core/proxy/api_client.dart';
import 'package:chagocnote/core/proxy/providers.dart';
import 'package:chagocnote/core/router/app_router.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/core/storage/token_store.dart';
import 'package:chagocnote/design/app_theme.dart';
import 'package:chagocnote/design/bridge/glass_surface.dart';
import 'package:chagocnote/features/auth/state/session.dart';
import 'package:chagocnote/features/auth/state/session_controller.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/fake_http_client_adapter.dart';
import '../../../support/fake_session_gateway.dart';

const _hissHaus = ShopMembership(shopId: 3, shopName: 'Hiss Haus', role: 'owner');
const _hissHausStaff = ShopMembership(shopId: 3, shopName: 'Hiss Haus', role: 'staff');

Me _ownerMe() => const Me(
      id: 99,
      displayName: '민석',
      profileImageUrl: null,
      identities: ['apple'],
      shops: [_hissHaus],
    );

Me _staffMe() => const Me(
      id: 50,
      displayName: '직원',
      profileImageUrl: null,
      identities: ['apple'],
      shops: [_hissHausStaff],
    );

const _membersJson = [
  {
    'member_id': 1,
    'user_id': 99,
    'display_name': '민석',
    'profile_image_url': null,
    'role': 'owner',
    'joined_at': '2026-01-01T00:00:00Z',
  },
  {
    'member_id': 21,
    'user_id': 50,
    'display_name': '직원',
    'profile_image_url': null,
    'role': 'staff',
    'joined_at': '2026-02-02T00:00:00Z',
  },
];

({ProviderContainer container, FakeHttpClientAdapter adapter}) _setUp(
  FakeSessionGateway gateway,
  FakeHandler handle,
) {
  final adapter = FakeHttpClientAdapter(handle);
  final dio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final container = ProviderContainer.test(
    retry: (retryCount, error) => null,
    overrides: [
      sessionGatewayProvider.overrideWithValue(gateway),
      apiClientProvider.overrideWith(
        (ref) => ApiClient(
          tokenStore: _NoopTokenStore(),
          dio: dio,
          refreshDio: dio,
          onSessionEnded: ref.read(sessionEndedSignalProvider).fire,
        ),
      ),
    ],
  );
  return (container: container, adapter: adapter);
}

Widget _appWith(ProviderContainer container) {
  return UncontrolledProviderScope(
    container: container,
    child: Consumer(
      builder: (context, ref, _) {
        final router = ref.watch(routerProvider);
        return MaterialApp.router(
          routerConfig: router,
          theme: appTheme(),
          builder: (context, child) => GlassBridge(
            factory: const OpaqueSurfaceFactory(),
            child: child!,
          ),
        );
      },
    ),
  );
}

void main() {
  testWidgets('직원은 관리 UI가 안 보인다', (tester) async {
    final gateway = FakeSessionGateway()..meOnRestore = _staffMe();
    final setup = _setUp(gateway, (options, body) {
      if (options.path == '/v1/shops/3/members') {
        return const FakeResponse(statusCode: 200, data: _membersJson);
      }
      fail('예상하지 못한 경로: ${options.path}');
    });
    addTearDown(setup.container.dispose);

    await tester.pumpWidget(_appWith(setup.container));
    await tester.pumpAndSettle();
    setup.container.read(routerProvider).go('/settings/members');
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.settingsMembers), findsOneWidget);
    expect(find.text(AppStrings.createInvite), findsNothing);
  });

  testWidgets('사장은 초대 코드 만들기 버튼을 본다', (tester) async {
    final gateway = FakeSessionGateway()..meOnRestore = _ownerMe();
    final setup = _setUp(gateway, (options, body) {
      if (options.path == '/v1/shops/3/members') {
        return const FakeResponse(statusCode: 200, data: _membersJson);
      }
      fail('예상하지 못한 경로: ${options.path}');
    });
    addTearDown(setup.container.dispose);

    await tester.pumpWidget(_appWith(setup.container));
    await tester.pumpAndSettle();
    setup.container.read(routerProvider).go('/settings/members');
    await tester.pumpAndSettle();

    expect(find.text(AppStrings.createInvite), findsOneWidget);
  });

  testWidgets('초대 코드를 만들면 코드를 보여주고 POST 요청을 보낸다', (tester) async {
    final gateway = FakeSessionGateway()..meOnRestore = _ownerMe();
    final setup = _setUp(gateway, (options, body) {
      if (options.path == '/v1/shops/3/members') {
        return const FakeResponse(statusCode: 200, data: _membersJson);
      }
      if (options.path == '/v1/shops/3/invites') {
        return const FakeResponse(
          statusCode: 201,
          data: {
            'code': 'ABC123',
            'role': 'staff',
            'expires_at': '2026-09-23T00:00:00Z',
          },
        );
      }
      fail('예상하지 못한 경로: ${options.path}');
    });
    addTearDown(setup.container.dispose);

    await tester.pumpWidget(_appWith(setup.container));
    await tester.pumpAndSettle();
    setup.container.read(routerProvider).go('/settings/members');
    await tester.pumpAndSettle();

    await tester.tap(find.text(AppStrings.createInvite));
    await tester.pumpAndSettle();

    expect(find.text('ABC123'), findsOneWidget);
    final invitePosts = setup.adapter.requests
        .where((r) => r.path == '/v1/shops/3/invites' && r.method == 'POST');
    expect(invitePosts, hasLength(1));
  });

  testWidgets('역할 변경은 PATCH 를 보내고 목록을 새로고침한다', (tester) async {
    final gateway = FakeSessionGateway()..meOnRestore = _ownerMe();
    var patched = false;
    final setup = _setUp(gateway, (options, body) {
      if (options.path == '/v1/shops/3/members') {
        return FakeResponse(
          statusCode: 200,
          data: patched
              ? [
                  _membersJson[0],
                  {..._membersJson[1], 'role': 'owner'},
                ]
              : _membersJson,
        );
      }
      if (options.path == '/v1/shops/3/members/21' && options.method == 'PATCH') {
        patched = true;
        return const FakeResponse(
          statusCode: 200,
          data: {'member_id': 21, 'user_id': 50, 'role': 'owner'},
        );
      }
      fail('예상하지 못한 경로: ${options.method} ${options.path}');
    });
    addTearDown(setup.container.dispose);

    await tester.pumpWidget(_appWith(setup.container));
    await tester.pumpAndSettle();
    setup.container.read(routerProvider).go('/settings/members');
    await tester.pumpAndSettle();

    await tester.tap(find.text('직원').first);
    await tester.pumpAndSettle();
    await tester.tap(find.text(AppStrings.promoteToOwner));
    await tester.pumpAndSettle();

    final patchRequest = setup.adapter.requests.firstWhere(
      (r) => r.path == '/v1/shops/3/members/21' && r.method == 'PATCH',
    );
    final sentBody =
        setup.adapter.lastBodyByPath['/v1/shops/3/members/21'];
    expect(patchRequest.method, 'PATCH');
    expect(String.fromCharCodes(sentBody!), '{"role":"owner"}');
  });

  testWidgets('내보내기는 확인 후 DELETE 를 보내고 목록을 새로고침한다', (tester) async {
    final gateway = FakeSessionGateway()..meOnRestore = _ownerMe();
    var removed = false;
    final setup = _setUp(gateway, (options, body) {
      if (options.path == '/v1/shops/3/members') {
        return FakeResponse(
          statusCode: 200,
          data: removed ? [_membersJson[0]] : _membersJson,
        );
      }
      if (options.path == '/v1/shops/3/members/21' &&
          options.method == 'DELETE') {
        removed = true;
        return const FakeResponse(statusCode: 204);
      }
      fail('예상하지 못한 경로: ${options.method} ${options.path}');
    });
    addTearDown(setup.container.dispose);

    await tester.pumpWidget(_appWith(setup.container));
    await tester.pumpAndSettle();
    setup.container.read(routerProvider).go('/settings/members');
    await tester.pumpAndSettle();

    await tester.tap(find.text('직원').first);
    await tester.pumpAndSettle();
    await tester.tap(find.text(AppStrings.removeMember));
    await tester.pumpAndSettle();
    // 확인 시트에도 같은 라벨의 버튼이 있다 — 마지막(확인 시트)을 누른다.
    await tester.tap(find.text(AppStrings.removeMember).last);
    await tester.pumpAndSettle();

    expect(
      setup.adapter.requests.where(
        (r) => r.path == '/v1/shops/3/members/21' && r.method == 'DELETE',
      ),
      hasLength(1),
    );
    expect(find.text('직원'), findsNothing);
  });

  testWidgets('LAST_OWNER 면 문구를 보여준다', (tester) async {
    final gateway = FakeSessionGateway()..meOnRestore = _ownerMe();
    final setup = _setUp(gateway, (options, body) {
      if (options.path == '/v1/shops/3/members') {
        return const FakeResponse(statusCode: 200, data: _membersJson);
      }
      if (options.path == '/v1/shops/3/members/21' && options.method == 'PATCH') {
        return const FakeResponse(
          statusCode: 409,
          data: {'code': 'LAST_OWNER', 'message': '마지막 사장'},
        );
      }
      fail('예상하지 못한 경로: ${options.method} ${options.path}');
    });
    addTearDown(setup.container.dispose);

    await tester.pumpWidget(_appWith(setup.container));
    await tester.pumpAndSettle();
    setup.container.read(routerProvider).go('/settings/members');
    await tester.pumpAndSettle();

    await tester.tap(find.text('직원').first);
    await tester.pumpAndSettle();
    await tester.tap(find.text(AppStrings.promoteToOwner));
    await tester.pumpAndSettle();

    expect(find.text('매장에는 사장이 한 명 이상 있어야 합니다.'), findsOneWidget);
  });

  testWidgets(
    'NOT_A_MEMBER 면 reloadMe 를 부른다 — 매장이 남아있으면 그대로 머무른다',
    (tester) async {
      final gateway = FakeSessionGateway()
        ..meOnRestore = _ownerMe()
        ..meOnRefresh = _ownerMe(); // 강등됐지만 여전히 멤버
      final setup = _setUp(gateway, (options, body) {
        if (options.path == '/v1/shops/3/members') {
          return const FakeResponse(statusCode: 200, data: _membersJson);
        }
        if (options.path == '/v1/shops/3/members/21' &&
            options.method == 'PATCH') {
          return const FakeResponse(
            statusCode: 403,
            data: {'code': 'NOT_A_MEMBER', 'message': '멤버 아님'},
          );
        }
        fail('예상하지 못한 경로: ${options.method} ${options.path}');
      });
      addTearDown(setup.container.dispose);

      await tester.pumpWidget(_appWith(setup.container));
      await tester.pumpAndSettle();
      setup.container.read(routerProvider).go('/settings/members');
      await tester.pumpAndSettle();

      await tester.tap(find.text('직원').first);
      await tester.pumpAndSettle();
      await tester.tap(find.text(AppStrings.promoteToOwner));
      await tester.pumpAndSettle();

      expect(gateway.refreshMeCallCount, 1);
      expect(find.byKey(ScreenKeys.settingsMembers), findsOneWidget);
    },
  );

  testWidgets(
    'NOT_A_MEMBER 면 reloadMe 를 부른다 — 매장이 사라졌으면 라우터가 내보낸다',
    (tester) async {
      final gateway = FakeSessionGateway()..meOnRestore = _ownerMe();
      final setup = _setUp(gateway, (options, body) {
        if (options.path == '/v1/shops/3/members') {
          return const FakeResponse(statusCode: 200, data: _membersJson);
        }
        if (options.path == '/v1/shops/3/members/21' &&
            options.method == 'PATCH') {
          return const FakeResponse(
            statusCode: 403,
            data: {'code': 'NOT_A_MEMBER', 'message': '멤버 아님'},
          );
        }
        fail('예상하지 못한 경로: ${options.method} ${options.path}');
      });
      // 제거됨 — 더는 이 매장의 멤버가 아니다.
      gateway.meOnRefresh = const Me(
        id: 99,
        displayName: '민석',
        profileImageUrl: null,
        identities: ['apple'],
        shops: [],
      );
      addTearDown(setup.container.dispose);

      await tester.pumpWidget(_appWith(setup.container));
      await tester.pumpAndSettle();
      setup.container.read(routerProvider).go('/settings/members');
      await tester.pumpAndSettle();

      await tester.tap(find.text('직원').first);
      await tester.pumpAndSettle();
      await tester.tap(find.text(AppStrings.promoteToOwner));
      await tester.pumpAndSettle();

      expect(gateway.refreshMeCallCount, 1);
      expect(find.byKey(ScreenKeys.invite), findsOneWidget);
    },
  );
}

class _NoopTokenStore implements TokenStore {
  @override
  Future<void> clear() async {}

  @override
  Future<String?> readAccess() async => null;

  @override
  Future<String?> readRefresh() async => null;

  @override
  Future<void> save({required String access, required String refresh}) async {}
}
```

`app/test/features/shop/screens/settings_screen_test.dart`:
```dart
import 'package:chagocnote/core/proxy/api_client.dart';
import 'package:chagocnote/core/proxy/providers.dart';
import 'package:chagocnote/core/router/app_router.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/core/storage/token_store.dart';
import 'package:chagocnote/design/app_theme.dart';
import 'package:chagocnote/design/bridge/glass_surface.dart';
import 'package:chagocnote/features/auth/state/session.dart';
import 'package:chagocnote/features/auth/state/session_controller.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/fake_http_client_adapter.dart';
import '../../../support/fake_session_gateway.dart';

const _hissHaus = ShopMembership(shopId: 3, shopName: 'Hiss Haus', role: 'owner');
const _staffShop = ShopMembership(shopId: 4, shopName: 'B매장', role: 'staff');

/// 이 화면 자체(설정 허브)는 매장 API를 부르지 않지만, 화면 전환 테스트가
/// 실제로 멤버 화면까지 들어가므로 그쪽이 부르는 매장 API를 가짜로 채워
/// 실제 네트워크 호출(그리고 그로 인한 pumpAndSettle 무한 대기)을 막는다.
ProviderContainer _containerWith(Me me, {int? lastShopId}) {
  final gateway = FakeSessionGateway()
    ..meOnRestore = me
    ..lastShopId = lastShopId;
  final adapter = FakeHttpClientAdapter(
    (options, body) => const FakeResponse(statusCode: 200, data: <dynamic>[]),
  );
  final dio = Dio(BaseOptions())..httpClientAdapter = adapter;
  return ProviderContainer.test(
    retry: (retryCount, error) => null,
    overrides: [
      sessionGatewayProvider.overrideWithValue(gateway),
      apiClientProvider.overrideWith(
        (ref) => ApiClient(
          tokenStore: _NoopTokenStore(),
          dio: dio,
          refreshDio: dio,
          onSessionEnded: ref.read(sessionEndedSignalProvider).fire,
        ),
      ),
    ],
  );
}

class _NoopTokenStore implements TokenStore {
  @override
  Future<void> clear() async {}

  @override
  Future<String?> readAccess() async => null;

  @override
  Future<String?> readRefresh() async => null;

  @override
  Future<void> save({required String access, required String refresh}) async {}
}

Widget _appWith(ProviderContainer container) {
  return UncontrolledProviderScope(
    container: container,
    child: Consumer(
      builder: (context, ref, _) {
        final router = ref.watch(routerProvider);
        return MaterialApp.router(
          routerConfig: router,
          theme: appTheme(),
          builder: (context, child) => GlassBridge(
            factory: const OpaqueSurfaceFactory(),
            child: child!,
          ),
        );
      },
    ),
  );
}

void main() {
  testWidgets('매장 이름과 역할 칩을 보여준다', (tester) async {
    final container = _containerWith(
      const Me(
        id: 1,
        displayName: '민석',
        profileImageUrl: null,
        identities: ['apple'],
        shops: [_hissHaus],
      ),
    );
    addTearDown(container.dispose);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();
    container.read(routerProvider).go('/settings');
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.settings), findsOneWidget);
    expect(find.text('Hiss Haus'), findsOneWidget);
    expect(find.text(AppStrings.roleOwner), findsOneWidget);
  });

  testWidgets('매장이 하나뿐이면 매장 바꾸기가 안 보인다', (tester) async {
    final container = _containerWith(
      const Me(
        id: 1,
        displayName: '민석',
        profileImageUrl: null,
        identities: ['apple'],
        shops: [_hissHaus],
      ),
    );
    addTearDown(container.dispose);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();
    container.read(routerProvider).go('/settings');
    await tester.pumpAndSettle();

    expect(find.text(AppStrings.settingsSwitchShop), findsNothing);
  });

  testWidgets('매장이 둘 이상이면 매장 바꾸기를 눌러 매장 선택 화면으로 간다', (tester) async {
    final container = _containerWith(
      const Me(
        id: 1,
        displayName: '민석',
        profileImageUrl: null,
        identities: ['apple'],
        shops: [_hissHaus, _staffShop],
      ),
      lastShopId: _hissHaus.shopId,
    );
    addTearDown(container.dispose);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();
    container.read(routerProvider).go('/settings');
    await tester.pumpAndSettle();

    expect(find.text(AppStrings.settingsSwitchShop), findsOneWidget);
    await tester.tap(find.text(AppStrings.settingsSwitchShop));
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.shopSelect), findsOneWidget);
  });

  testWidgets('멤버를 누르면 멤버 화면으로 간다', (tester) async {
    final container = _containerWith(
      const Me(
        id: 1,
        displayName: '민석',
        profileImageUrl: null,
        identities: ['apple'],
        shops: [_hissHaus],
      ),
    );
    addTearDown(container.dispose);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();
    container.read(routerProvider).go('/settings');
    await tester.pumpAndSettle();

    await tester.tap(find.text(AppStrings.settingsMembers));
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.settingsMembers), findsOneWidget);
  });

  testWidgets('초대 코드로 합류를 누르면 초대 화면으로 간다', (tester) async {
    final container = _containerWith(
      const Me(
        id: 1,
        displayName: '민석',
        profileImageUrl: null,
        identities: ['apple'],
        shops: [_hissHaus],
      ),
    );
    addTearDown(container.dispose);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();
    container.read(routerProvider).go('/settings');
    await tester.pumpAndSettle();

    await tester.tap(find.text(AppStrings.settingsJoinByInvite));
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.invite), findsOneWidget);
  });
}
```

`app/test/support/fake_session_gateway.dart` — 바꾼다:
```diff
--- a/test/support/fake_session_gateway.dart
+++ b/test/support/fake_session_gateway.dart
@@ -21,6 +21,9 @@ class FakeSessionGateway implements SessionGateway {
   Me? meOnRefresh;
   Object? refreshMeError;
 
+  /// refreshMe() 가 호출된 횟수.
+  int refreshMeCallCount = 0;
+
   bool signOutCalled = false;
   int? writtenShopId;
 
@@ -45,6 +48,7 @@ class FakeSessionGateway implements SessionGateway {
 
   @override
   Future<Me> refreshMe() async {
+    refreshMeCallCount++;
     if (refreshMeError != null) throw refreshMeError!;
     return meOnRefresh!;
   }
```

Run: `flutter test test/features/shop`
Expected: FAIL — `shop_api.dart` 등이 없다.

- [ ] **Step 2: 구현한다**

`app/lib/core/router/app_router.dart` — 바꾼다:
```diff
--- a/lib/core/router/app_router.dart
+++ b/lib/core/router/app_router.dart
@@ -9,6 +9,8 @@ import '../../features/auth/screens/splash_screen.dart';
 import '../../features/auth/state/session.dart';
 import '../../features/auth/state/session_controller.dart';
 import '../../features/home/screens/home_shell.dart';
+import '../../features/shop/screens/members_screen.dart';
+import '../../features/shop/screens/settings_screen.dart';
 import 'placeholder_screens.dart';
 
 /// go_router의 `refreshListenable`은 평범한 [Listenable]을 요구한다. 세션이
@@ -76,7 +78,7 @@ final routerProvider = Provider<GoRouter>((ref) {
       ),
       GoRoute(
         path: '/settings/members',
-        builder: (context, state) => const SettingsMembersScreen(),
+        builder: (context, state) => const MembersScreen(),
       ),
       GoRoute(
         path: '/settings/shop',
```

`app/lib/core/router/placeholder_screens.dart` — 바꾼다:
```diff
--- a/lib/core/router/placeholder_screens.dart
+++ b/lib/core/router/placeholder_screens.dart
@@ -16,26 +16,6 @@ class _PlaceholderScreen extends StatelessWidget {
   }
 }
 
-class SettingsScreen extends StatelessWidget {
-  const SettingsScreen({super.key});
-
-  @override
-  Widget build(BuildContext context) => const _PlaceholderScreen(
-        label: 'settings',
-        screenKey: ScreenKeys.settings,
-      );
-}
-
-class SettingsMembersScreen extends StatelessWidget {
-  const SettingsMembersScreen({super.key});
-
-  @override
-  Widget build(BuildContext context) => const _PlaceholderScreen(
-        label: 'settings_members',
-        screenKey: ScreenKeys.settingsMembers,
-      );
-}
-
 class SettingsShopScreen extends StatelessWidget {
   const SettingsShopScreen({super.key});
 
```

`app/lib/features/shop/api/shop_api.dart`:
```dart
import '../../../core/proxy/api_client.dart';

/// 매장 멤버 한 명.
class ShopMember {
  const ShopMember({
    required this.memberId,
    required this.userId,
    required this.displayName,
    required this.profileImageUrl,
    required this.role,
    required this.joinedAt,
  });

  factory ShopMember.fromJson(Map<String, dynamic> json) => ShopMember(
        memberId: json['member_id'] as int,
        userId: json['user_id'] as int,
        displayName: json['display_name'] as String,
        profileImageUrl: json['profile_image_url'] as String?,
        role: json['role'] as String,
        joinedAt: DateTime.parse(json['joined_at'] as String),
      );

  final int memberId;
  final int userId;
  final String displayName;
  final String? profileImageUrl;

  /// 'owner' | 'staff'
  final String role;
  final DateTime joinedAt;

  bool get isOwner => role == 'owner';
}

/// 새로 만든 초대 코드. 코드 값이 로그에 찍히지 않도록 `toString`을
/// 오버라이드하지 않는다.
class CreatedInvite {
  const CreatedInvite({
    required this.code,
    required this.role,
    required this.expiresAt,
  });

  factory CreatedInvite.fromJson(Map<String, dynamic> json) => CreatedInvite(
        code: json['code'] as String,
        role: json['role'] as String,
        expiresAt: DateTime.parse(json['expires_at'] as String),
      );

  final String code;
  final String role;
  final DateTime expiresAt;
}

/// 매장 정보.
class ShopSettings {
  const ShopSettings({
    required this.shopId,
    required this.name,
    required this.businessType,
    required this.phone,
    required this.address,
    required this.timezone,
  });

  factory ShopSettings.fromJson(Map<String, dynamic> json) => ShopSettings(
        shopId: json['shop_id'] as int,
        name: json['name'] as String,
        businessType: json['business_type'] as String,
        phone: json['phone'] as String?,
        address: json['address'] as String?,
        timezone: json['timezone'] as String,
      );

  final int shopId;
  final String name;
  final String businessType;
  final String? phone;
  final String? address;
  final String timezone;
}

/// 매장 범위 API — 멤버 관리, 초대, 매장 정보.
class ShopApi {
  ShopApi(this._client);

  final ApiClient _client;

  Future<List<ShopMember>> members(int shopId) async {
    final data = await _client.get('/v1/shops/$shopId/members') as List;
    return data
        .map((e) => ShopMember.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<CreatedInvite> createInvite(int shopId) async {
    final data =
        await _client.post('/v1/shops/$shopId/invites') as Map<String, dynamic>;
    return CreatedInvite.fromJson(data);
  }

  Future<void> changeRole(int shopId, int memberId, String role) {
    return _client.patch(
      '/v1/shops/$shopId/members/$memberId',
      data: {'role': role},
    );
  }

  Future<void> removeMember(int shopId, int memberId) {
    return _client.delete('/v1/shops/$shopId/members/$memberId');
  }

  Future<ShopSettings> settings(int shopId) async {
    final data = await _client.get('/v1/shops/$shopId/settings')
        as Map<String, dynamic>;
    return ShopSettings.fromJson(data);
  }

  Future<ShopSettings> updateSettings(
    int shopId, {
    required String name,
    String? phone,
    String? address,
  }) async {
    final data = await _client.put(
      '/v1/shops/$shopId/settings',
      data: {'name': name, 'phone': phone, 'address': address},
    ) as Map<String, dynamic>;
    return ShopSettings.fromJson(data);
  }
}
```

`app/lib/features/shop/screens/members_screen.dart`:
```dart
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/error/error_messages.dart';
import '../../../core/router/screen_keys.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_button.dart';
import '../../../design/widgets/app_chip.dart';
import '../../../design/widgets/app_glass_card.dart';
import '../../../design/widgets/app_photo_tile.dart';
import '../../../design/widgets/app_sheet.dart';
import '../../../design/widgets/pressable.dart';
import '../../../l10n/app_strings.dart';
import '../../auth/state/session.dart';
import '../../auth/state/session_controller.dart';
import '../api/shop_api.dart';
import '../state/members_controller.dart';

/// 매장 멤버 목록. 사장은 초대 코드 발급과 멤버 관리(역할 변경·내보내기)를
/// 함께 볼 수 있다. 직원은 목록만 본다.
class MembersScreen extends ConsumerStatefulWidget {
  const MembersScreen({super.key});

  @override
  ConsumerState<MembersScreen> createState() => _MembersScreenState();
}

class _MembersScreenState extends ConsumerState<MembersScreen> {
  String? _errorText;

  int? get _shopId {
    final session = ref.read(sessionControllerProvider).value;
    return session is SignedIn ? session.selectedShopId : null;
  }

  Future<void> _createInvite() async {
    final shopId = _shopId;
    if (shopId == null) return;
    setState(() => _errorText = null);
    try {
      final invite =
          await ref.read(membersControllerProvider(shopId).notifier).createInvite();
      if (!mounted) return;
      _showInviteSheet(invite);
    } catch (e) {
      if (!mounted) return;
      setState(() => _errorText = messageFor(e));
    }
  }

  void _showInviteSheet(CreatedInvite invite) {
    AppSheet.show<void>(
      context,
      builder: (context) => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            invite.code,
            style: AppTypography.bigNumeral.copyWith(fontSize: 40),
          ),
          const SizedBox(height: AppSpacing.sm),
          Text(
            '${AppStrings.inviteExpiresAtLabel} ${_formatDate(invite.expiresAt)}',
            style: AppTypography.caption,
          ),
          const SizedBox(height: AppSpacing.lg),
          AppButton(
            label: AppStrings.copy,
            onPressed: () => Clipboard.setData(ClipboardData(text: invite.code)),
          ),
        ],
      ),
    );
  }

  Future<void> _openMemberActions(ShopMember member) async {
    final action = await AppSheet.show<String>(
      context,
      builder: (context) => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          _ActionRow(
            label: member.isOwner
                ? AppStrings.demoteToStaff
                : AppStrings.promoteToOwner,
            onTap: () => Navigator.of(context)
                .pop(member.isOwner ? 'staff' : 'owner'),
          ),
          _ActionRow(
            label: AppStrings.removeMember,
            onTap: () => Navigator.of(context).pop('remove'),
          ),
        ],
      ),
    );
    if (action == null || !mounted) return;

    final shopId = _shopId;
    if (shopId == null) return;

    if (action == 'remove') {
      final confirmed = await _confirmRemove();
      if (confirmed != true || !mounted) return;
      await _run(
        () => ref
            .read(membersControllerProvider(shopId).notifier)
            .remove(member.memberId),
      );
      return;
    }

    await _run(
      () => ref
          .read(membersControllerProvider(shopId).notifier)
          .changeRole(member.memberId, action),
    );
  }

  Future<bool?> _confirmRemove() {
    return AppSheet.show<bool>(
      context,
      builder: (context) => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            AppStrings.removeMemberConfirmTitle,
            style: AppTypography.body,
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: AppSpacing.lg),
          AppButton(
            label: AppStrings.removeMember,
            filled: true,
            onPressed: () => Navigator.of(context).pop(true),
          ),
          const SizedBox(height: AppSpacing.sm),
          AppButton(
            label: AppStrings.cancel,
            onPressed: () => Navigator.of(context).pop(false),
          ),
        ],
      ),
    );
  }

  Future<void> _run(Future<void> Function() action) async {
    setState(() => _errorText = null);
    try {
      await action();
    } catch (e) {
      if (!mounted) return;
      setState(() => _errorText = messageFor(e));
    }
  }

  static String _formatDate(DateTime date) =>
      '${date.year}.${date.month.toString().padLeft(2, '0')}.${date.day.toString().padLeft(2, '0')}';

  @override
  Widget build(BuildContext context) {
    final shopId = _shopId;
    final session = ref.watch(sessionControllerProvider).value;
    final isOwner =
        session is SignedIn && (session.selectedShop?.isOwner ?? false);
    final myUserId = session is SignedIn ? session.me.id : null;
    final members = shopId == null
        ? const AsyncValue<List<ShopMember>>.data(<ShopMember>[])
        : ref.watch(membersControllerProvider(shopId));

    return Scaffold(
      key: ScreenKeys.settingsMembers,
      body: AppBackground(
        child: SafeArea(
          child: Column(
            children: [
              Padding(
                padding: const EdgeInsets.all(AppSpacing.lg),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      AppStrings.settingsMembers,
                      style: AppTypography.titleKo,
                    ),
                    if (isOwner)
                      AppButton(
                        label: AppStrings.createInvite,
                        onPressed: _createInvite,
                      ),
                  ],
                ),
              ),
              if (_errorText != null)
                Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: AppSpacing.lg,
                  ),
                  child: Text(
                    _errorText!,
                    style: AppTypography.caption,
                  ),
                ),
              Expanded(
                child: members.when(
                  data: (list) => ListView.builder(
                    padding: const EdgeInsets.all(AppSpacing.lg),
                    itemCount: list.length,
                    itemBuilder: (context, index) {
                      final member = list[index];
                      final isSelf = member.userId == myUserId;
                      final canManage = isOwner && !isSelf;
                      return Padding(
                        padding: const EdgeInsets.only(bottom: AppSpacing.sm),
                        child: Pressable(
                          onTap: canManage
                              ? () => _openMemberActions(member)
                              : null,
                          semanticLabel: member.displayName,
                          child: AppGlassCard(
                            child: Row(
                              children: [
                                AppPhotoTile(
                                  image: member.profileImageUrl != null
                                      ? NetworkImage(member.profileImageUrl!)
                                      : null,
                                  size: 40,
                                ),
                                const SizedBox(width: AppSpacing.md),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        member.displayName,
                                        style: AppTypography.bodyStrong,
                                      ),
                                      Text(
                                        _formatDate(member.joinedAt),
                                        style: AppTypography.caption,
                                      ),
                                    ],
                                  ),
                                ),
                                AppChip(
                                  label: member.isOwner
                                      ? AppStrings.roleOwner
                                      : AppStrings.roleStaff,
                                ),
                              ],
                            ),
                          ),
                        ),
                      );
                    },
                  ),
                  loading: () =>
                      const Center(child: CircularProgressIndicator()),
                  error: (error, _) =>
                      Center(child: Text(messageFor(error), style: AppTypography.body)),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ActionRow extends StatelessWidget {
  const _ActionRow({required this.label, required this.onTap});

  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Pressable(
      onTap: onTap,
      semanticLabel: label,
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(vertical: AppSpacing.md),
        alignment: Alignment.center,
        child: Text(label, style: AppTypography.body),
      ),
    );
  }
}
```

`app/lib/features/shop/screens/settings_screen.dart`:
```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/router/screen_keys.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens/app_colors.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_chip.dart';
import '../../../design/widgets/pressable.dart';
import '../../../l10n/app_strings.dart';
import '../../auth/state/session.dart';
import '../../auth/state/session_controller.dart';

/// 설정 허브. 매장/다른 매장/계정 세 묶음으로 이동한다.
class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final session = ref.watch(sessionControllerProvider).value;
    final shop = session is SignedIn ? session.selectedShop : null;
    final shopCount = session is SignedIn ? session.me.shops.length : 0;

    return Scaffold(
      key: ScreenKeys.settings,
      body: AppBackground(
        child: SafeArea(
          child: ListView(
            padding: const EdgeInsets.all(AppSpacing.lg),
            children: [
              if (shop != null) ...[
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(shop.shopName, style: AppTypography.titleKo),
                    AppChip(
                      label: shop.isOwner
                          ? AppStrings.roleOwner
                          : AppStrings.roleStaff,
                    ),
                  ],
                ),
                const SizedBox(height: AppSpacing.xl),
              ],
              const _SectionLabel(AppStrings.settingsSectionShop),
              _SettingsRow(
                label: AppStrings.settingsMembers,
                onTap: () => context.push('/settings/members'),
              ),
              _SettingsRow(
                label: AppStrings.settingsShopInfo,
                onTap: () => context.push('/settings/shop'),
              ),
              const SizedBox(height: AppSpacing.xl),
              const _SectionLabel(AppStrings.settingsSectionOtherShops),
              if (shopCount >= 2)
                _SettingsRow(
                  label: AppStrings.settingsSwitchShop,
                  onTap: () => context.push('/shops/select'),
                ),
              _SettingsRow(
                label: AppStrings.settingsJoinByInvite,
                onTap: () => context.push('/invite'),
              ),
              const SizedBox(height: AppSpacing.xl),
              const _SectionLabel(AppStrings.settingsSectionAccount),
              _SettingsRow(
                label: AppStrings.settingsAccount,
                onTap: () => context.push('/settings/account'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _SectionLabel extends StatelessWidget {
  const _SectionLabel(this.label);

  final String label;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: Text(label, style: AppTypography.caption),
    );
  }
}

class _SettingsRow extends StatelessWidget {
  const _SettingsRow({required this.label, required this.onTap});

  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Pressable(
      onTap: onTap,
      semanticLabel: label,
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(vertical: AppSpacing.md),
        decoration: const BoxDecoration(
          border: Border(bottom: BorderSide(color: AppColors.line)),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(label, style: AppTypography.body),
            const Icon(
              Icons.chevron_right,
              size: 18,
              color: AppColors.secondary,
            ),
          ],
        ),
      ),
    );
  }
}
```

`app/lib/features/shop/state/members_controller.dart`:
```dart
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../auth/state/session.dart';
import '../../auth/state/session_controller.dart';
import '../api/shop_api.dart';
import 'shop_errors.dart';
import 'shop_providers.dart';

/// 매장 하나의 멤버 목록과 그 관리 동작. 매장 id로 만든
/// [membersControllerProvider] family가 매장마다 별도 인스턴스를 준다.
class MembersController extends AsyncNotifier<List<ShopMember>> {
  MembersController(this.shopId);

  final int shopId;

  ShopApi get _api => ref.read(shopApiProvider);

  @override
  Future<List<ShopMember>> build() => _api.members(shopId);

  Future<void> _reload() async {
    state = AsyncData(await _api.members(shopId));
  }

  int? _userIdFor(int memberId) {
    for (final member in state.value ?? const <ShopMember>[]) {
      if (member.memberId == memberId) return member.userId;
    }
    return null;
  }

  bool _isCurrentUser(int userId) {
    final session = ref.read(sessionControllerProvider).value;
    return session is SignedIn && session.me.id == userId;
  }

  Future<CreatedInvite> createInvite() {
    return runShopScoped(ref, () async {
      final result = await _api.createInvite(shopId);
      await _reload();
      return result;
    });
  }

  Future<void> changeRole(int memberId, String role) {
    return runShopScoped(ref, () async {
      final userId = _userIdFor(memberId);
      await _api.changeRole(shopId, memberId, role);
      await _reload();
      if (userId != null && _isCurrentUser(userId)) {
        await ref.read(sessionControllerProvider.notifier).reloadMe();
      }
    });
  }

  Future<void> remove(int memberId) {
    return runShopScoped(ref, () async {
      final userId = _userIdFor(memberId);
      await _api.removeMember(shopId, memberId);
      await _reload();
      if (userId != null && _isCurrentUser(userId)) {
        await ref.read(sessionControllerProvider.notifier).reloadMe();
      }
    });
  }
}

final membersControllerProvider =
    AsyncNotifierProvider.family<MembersController, List<ShopMember>, int>(
  MembersController.new,
);
```

`app/lib/features/shop/state/shop_errors.dart`:
```dart
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/error/api_exception.dart';
import '../../auth/state/session_controller.dart';

/// 매장 범위 호출 공통 오류 처리.
///
/// 어떤 매장 범위 호출이든 `NOT_A_MEMBER`(제거되었거나 역할이 바뀐 경우)를
/// 받을 수 있다. 이때 매장을 로컬에서 지우지 않고 본인 정보만 다시
/// 불러와 라우터가 다시 평가하게 한다 — 강등된 멤버는 여전히 멤버라 그대로
/// 머무르고, 제거된 멤버는 라우터가 알아서 내보낸다. 그 외 오류는 그대로
/// 다시 던져서 화면이 문구로 보여주게 한다.
Future<T> runShopScoped<T>(Ref ref, Future<T> Function() action) async {
  try {
    return await action();
  } on ApiException catch (e) {
    if (e.code == 'NOT_A_MEMBER') {
      await ref.read(sessionControllerProvider.notifier).reloadMe();
    }
    rethrow;
  }
}
```

`app/lib/features/shop/state/shop_providers.dart`:
```dart
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/proxy/providers.dart';
import '../api/shop_api.dart';

final shopApiProvider = Provider<ShopApi>(
  (ref) => ShopApi(ref.watch(apiClientProvider)),
);
```

`app/lib/l10n/app_strings.dart` — 바꾼다:
```diff
--- a/lib/l10n/app_strings.dart
+++ b/lib/l10n/app_strings.dart
@@ -38,4 +38,32 @@ class AppStrings {
   static const calendarEmptyCaption = '예약을 만들면 여기에서 모아 볼 수 있어요.';
   static const comingSoonEmptyTitle = '준비 중입니다';
   static const comingSoonSheetText = '예약과 기록은 다음 업데이트에서 만나요';
+
+  // 설정 허브
+  static const settingsSectionShop = '매장';
+  static const settingsSectionOtherShops = '다른 매장';
+  static const settingsSectionAccount = '계정';
+  static const settingsMembers = '멤버';
+  static const settingsShopInfo = '매장 정보';
+  static const settingsSwitchShop = '매장 바꾸기';
+  static const settingsJoinByInvite = '초대 코드로 합류';
+  static const settingsAccount = '계정';
+
+  // 멤버
+  static const createInvite = '초대 코드 만들기';
+  static const inviteExpiresAtLabel = '만료';
+  static const copy = '복사';
+  static const promoteToOwner = '사장으로 변경';
+  static const demoteToStaff = '직원으로 변경';
+  static const removeMember = '내보내기';
+  static const removeMemberConfirmTitle = '정말 내보낼까요?';
+  static const cancel = '취소';
+
+  // 매장 정보
+  static const shopName = '매장 이름';
+  static const shopPhone = '전화번호';
+  static const shopAddress = '주소';
+  static const save = '저장';
+  static const saved = '저장했습니다';
+  static const shopNameRequired = '매장 이름을 입력해 주세요.';
 }
```

- [ ] **Step 3: 통과를 확인한다**

Run: `flutter test && flutter analyze`
Expected: `All tests passed!` (새 테스트 13개), `No issues found!`

- [ ] **Step 4: 판별력을 확인한다**

`members_screen.dart` 에서 관리 UI 를 감싸는 `isOwner` 분기를 잠깐 `true` 로 바꾸면 `직원은 관리 UI가 안 보인다` 테스트가 실패해야 한다. `shop_errors.dart` 의 `reloadMe()` 호출을 잠깐 지우면 `NOT_A_MEMBER` 테스트 둘이 실패해야 한다. 확인한 뒤 되돌린다.

- [ ] **Step 5: 커밋**

```bash
git add app/lib app/test
git commit -m "feat(app): 설정 허브와 멤버 관리 — 초대 코드, 역할 변경, 내보내기"
```

### Task 11: 매장 정보 보기와 수정

**Files:**
- Create: `app/lib/features/shop/state/shop_settings_controller.dart`, `app/lib/features/shop/screens/shop_settings_screen.dart`
- Modify: `app/lib/core/router/app_router.dart`, `app/lib/core/router/placeholder_screens.dart`
- Test: `app/test/features/shop/screens/shop_settings_screen_test.dart`

**Interfaces:**
- Consumes: `ShopApi.settings`·`updateSettings`·`runShopScoped`·`shopApiProvider`(Task 10), `sessionControllerProvider`
- Produces: `shopSettingsControllerProvider`(`AsyncNotifierProvider.family`, 인자 `shopId`), `ShopSettingsScreen`(`/settings/shop`)

규칙
- 사장: 이름(필수, 앞뒤 공백 제거, 1~50자)·전화·주소를 고치고 "저장" → `PUT` 으로 **폼 전체**를 보낸다(빈 전화·주소는 `null`). 저장에 성공하면 "저장했습니다"를 보여 주고, 이름이 바뀌었을 수 있으니 `reloadMe()` 로 홈의 매장 이름을 맞춘다.
- 직원: 읽기 전용이다. 저장 버튼이 없다.
- 이름이 비면 요청을 보내지 않는다. `NOT_A_MEMBER` 는 Task 10 의 도우미를 그대로 쓴다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`app/test/features/shop/screens/shop_settings_screen_test.dart`:
```dart
// 매장 정보 화면을 실제 라우터 + 가짜 HTTP 어댑터로 검증한다.
// 멤버 화면 테스트와 같은 이유로 `sessionGatewayProvider`는
// `FakeSessionGateway`, 매장 API는 `apiClientProvider`를 가짜 어댑터로
// 문 진짜 `ShopApi`로 검증한다.
import 'dart:convert';

import 'package:chagocnote/core/proxy/api_client.dart';
import 'package:chagocnote/core/proxy/providers.dart';
import 'package:chagocnote/core/router/app_router.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/core/storage/token_store.dart';
import 'package:chagocnote/design/app_theme.dart';
import 'package:chagocnote/design/bridge/glass_surface.dart';
import 'package:chagocnote/features/auth/state/session.dart';
import 'package:chagocnote/features/auth/state/session_controller.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/fake_http_client_adapter.dart';
import '../../../support/fake_session_gateway.dart';

const _hissHausOwner = ShopMembership(shopId: 3, shopName: 'Hiss Haus', role: 'owner');
const _hissHausStaff = ShopMembership(shopId: 3, shopName: 'Hiss Haus', role: 'staff');

const _settingsJson = {
  'shop_id': 3,
  'name': 'Hiss Haus',
  'business_type': 'grooming',
  'phone': '02-1234-5678',
  'address': '서울시 강남구',
  'timezone': 'Asia/Seoul',
};

({ProviderContainer container, FakeHttpClientAdapter adapter}) _setUp(
  FakeSessionGateway gateway,
  FakeHandler handle,
) {
  final adapter = FakeHttpClientAdapter(handle);
  final dio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final container = ProviderContainer.test(
    retry: (retryCount, error) => null,
    overrides: [
      sessionGatewayProvider.overrideWithValue(gateway),
      apiClientProvider.overrideWith(
        (ref) => ApiClient(
          tokenStore: _NoopTokenStore(),
          dio: dio,
          refreshDio: dio,
          onSessionEnded: ref.read(sessionEndedSignalProvider).fire,
        ),
      ),
    ],
  );
  return (container: container, adapter: adapter);
}

Widget _appWith(ProviderContainer container) {
  return UncontrolledProviderScope(
    container: container,
    child: Consumer(
      builder: (context, ref, _) {
        final router = ref.watch(routerProvider);
        return MaterialApp.router(
          routerConfig: router,
          theme: appTheme(),
          builder: (context, child) => GlassBridge(
            factory: const OpaqueSurfaceFactory(),
            child: child!,
          ),
        );
      },
    ),
  );
}

void main() {
  testWidgets('직원은 읽기 전용으로 보고 저장 버튼이 없다', (tester) async {
    final gateway = FakeSessionGateway()
      ..meOnRestore = const Me(
        id: 1,
        displayName: '직원',
        profileImageUrl: null,
        identities: ['apple'],
        shops: [_hissHausStaff],
      );
    final setup = _setUp(gateway, (options, body) {
      if (options.path == '/v1/shops/3/settings' && options.method == 'GET') {
        return const FakeResponse(statusCode: 200, data: _settingsJson);
      }
      fail('예상하지 못한 경로: ${options.method} ${options.path}');
    });
    addTearDown(setup.container.dispose);

    await tester.pumpWidget(_appWith(setup.container));
    await tester.pumpAndSettle();
    setup.container.read(routerProvider).go('/settings/shop');
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.settingsShop), findsOneWidget);
    expect(find.text(AppStrings.save), findsNothing);
    final nameField = tester.widget<TextField>(find.byType(TextField).first);
    expect(nameField.enabled, isFalse);
  });

  testWidgets('사장이 저장하면 정확한 JSON 본문으로 PUT 을 보낸다', (tester) async {
    final gateway = FakeSessionGateway()
      ..meOnRestore = const Me(
        id: 1,
        displayName: '민석',
        profileImageUrl: null,
        identities: ['apple'],
        shops: [_hissHausOwner],
      )
      ..meOnRefresh = const Me(
        id: 1,
        displayName: '민석',
        profileImageUrl: null,
        identities: ['apple'],
        shops: [_hissHausOwner],
      );
    final setup = _setUp(gateway, (options, body) {
      if (options.path == '/v1/shops/3/settings' && options.method == 'GET') {
        return const FakeResponse(statusCode: 200, data: _settingsJson);
      }
      if (options.path == '/v1/shops/3/settings' && options.method == 'PUT') {
        return const FakeResponse(
          statusCode: 200,
          data: {
            'shop_id': 3,
            'name': '새 이름',
            'business_type': 'grooming',
            'phone': null,
            'address': null,
            'timezone': 'Asia/Seoul',
          },
        );
      }
      fail('예상하지 못한 경로: ${options.method} ${options.path}');
    });
    addTearDown(setup.container.dispose);

    await tester.pumpWidget(_appWith(setup.container));
    await tester.pumpAndSettle();
    setup.container.read(routerProvider).go('/settings/shop');
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextField).at(0), '새 이름');
    await tester.enterText(find.byType(TextField).at(1), '');
    await tester.enterText(find.byType(TextField).at(2), '');
    await tester.tap(find.text(AppStrings.save));
    await tester.pumpAndSettle();

    expect(find.text(AppStrings.saved), findsOneWidget);
    final sentBody = setup.adapter.lastBodyByPath['/v1/shops/3/settings'];
    expect(
      utf8.decode(sentBody!),
      '{"name":"새 이름","phone":null,"address":null}',
    );
  });

  testWidgets('이름이 비어 있으면 요청 없이 검증만 한다', (tester) async {
    final gateway = FakeSessionGateway()
      ..meOnRestore = const Me(
        id: 1,
        displayName: '민석',
        profileImageUrl: null,
        identities: ['apple'],
        shops: [_hissHausOwner],
      );
    final setup = _setUp(gateway, (options, body) {
      if (options.path == '/v1/shops/3/settings' && options.method == 'GET') {
        return const FakeResponse(statusCode: 200, data: _settingsJson);
      }
      fail('예상하지 못한 경로: ${options.method} ${options.path}');
    });
    addTearDown(setup.container.dispose);

    await tester.pumpWidget(_appWith(setup.container));
    await tester.pumpAndSettle();
    setup.container.read(routerProvider).go('/settings/shop');
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextField).at(0), '   ');
    await tester.tap(find.text(AppStrings.save));
    await tester.pump();

    expect(find.text(AppStrings.shopNameRequired), findsOneWidget);
    expect(
      setup.adapter.requests.where((r) => r.method == 'PUT'),
      isEmpty,
    );
  });

  testWidgets('VALIDATION_ERROR 면 문구를 보여준다', (tester) async {
    final gateway = FakeSessionGateway()
      ..meOnRestore = const Me(
        id: 1,
        displayName: '민석',
        profileImageUrl: null,
        identities: ['apple'],
        shops: [_hissHausOwner],
      );
    final setup = _setUp(gateway, (options, body) {
      if (options.path == '/v1/shops/3/settings' && options.method == 'GET') {
        return const FakeResponse(statusCode: 200, data: _settingsJson);
      }
      if (options.path == '/v1/shops/3/settings' && options.method == 'PUT') {
        return const FakeResponse(
          statusCode: 422,
          data: {'code': 'VALIDATION_ERROR', 'message': '잘못됨'},
        );
      }
      fail('예상하지 못한 경로: ${options.method} ${options.path}');
    });
    addTearDown(setup.container.dispose);

    await tester.pumpWidget(_appWith(setup.container));
    await tester.pumpAndSettle();
    setup.container.read(routerProvider).go('/settings/shop');
    await tester.pumpAndSettle();

    await tester.tap(find.text(AppStrings.save));
    await tester.pumpAndSettle();

    expect(find.text('입력한 내용을 확인해 주세요.'), findsOneWidget);
  });

  testWidgets('NOT_A_MEMBER 면 reloadMe 를 부른다', (tester) async {
    final gateway = FakeSessionGateway()
      ..meOnRestore = const Me(
        id: 1,
        displayName: '민석',
        profileImageUrl: null,
        identities: ['apple'],
        shops: [_hissHausOwner],
      )
      ..meOnRefresh = const Me(
        id: 1,
        displayName: '민석',
        profileImageUrl: null,
        identities: ['apple'],
        shops: [_hissHausStaff],
      );
    final setup = _setUp(gateway, (options, body) {
      if (options.path == '/v1/shops/3/settings' && options.method == 'GET') {
        return const FakeResponse(statusCode: 200, data: _settingsJson);
      }
      if (options.path == '/v1/shops/3/settings' && options.method == 'PUT') {
        return const FakeResponse(
          statusCode: 403,
          data: {'code': 'NOT_A_MEMBER', 'message': '멤버 아님'},
        );
      }
      fail('예상하지 못한 경로: ${options.method} ${options.path}');
    });
    addTearDown(setup.container.dispose);

    await tester.pumpWidget(_appWith(setup.container));
    await tester.pumpAndSettle();
    setup.container.read(routerProvider).go('/settings/shop');
    await tester.pumpAndSettle();

    await tester.tap(find.text(AppStrings.save));
    await tester.pumpAndSettle();

    expect(gateway.refreshMeCallCount, 1);
    expect(find.byKey(ScreenKeys.settingsShop), findsOneWidget);
  });
}

class _NoopTokenStore implements TokenStore {
  @override
  Future<void> clear() async {}

  @override
  Future<String?> readAccess() async => null;

  @override
  Future<String?> readRefresh() async => null;

  @override
  Future<void> save({required String access, required String refresh}) async {}
}
```

Run: `flutter test test/features/shop/screens/shop_settings_screen_test.dart`
Expected: FAIL

- [ ] **Step 2: 구현한다**

`app/lib/core/router/app_router.dart` — 바꾼다:
```diff
--- a/lib/core/router/app_router.dart
+++ b/lib/core/router/app_router.dart
@@ -11,6 +11,7 @@ import '../../features/auth/state/session_controller.dart';
 import '../../features/home/screens/home_shell.dart';
 import '../../features/shop/screens/members_screen.dart';
 import '../../features/shop/screens/settings_screen.dart';
+import '../../features/shop/screens/shop_settings_screen.dart';
 import 'placeholder_screens.dart';
 
 /// go_router의 `refreshListenable`은 평범한 [Listenable]을 요구한다. 세션이
@@ -82,7 +83,7 @@ final routerProvider = Provider<GoRouter>((ref) {
       ),
       GoRoute(
         path: '/settings/shop',
-        builder: (context, state) => const SettingsShopScreen(),
+        builder: (context, state) => const ShopSettingsScreen(),
       ),
       GoRoute(
         path: '/settings/account',
```

`app/lib/core/router/placeholder_screens.dart` — 바꾼다:
```diff
--- a/lib/core/router/placeholder_screens.dart
+++ b/lib/core/router/placeholder_screens.dart
@@ -16,16 +16,6 @@ class _PlaceholderScreen extends StatelessWidget {
   }
 }
 
-class SettingsShopScreen extends StatelessWidget {
-  const SettingsShopScreen({super.key});
-
-  @override
-  Widget build(BuildContext context) => const _PlaceholderScreen(
-        label: 'settings_shop',
-        screenKey: ScreenKeys.settingsShop,
-      );
-}
-
 class SettingsAccountScreen extends StatelessWidget {
   const SettingsAccountScreen({super.key});
 
```

`app/lib/features/shop/screens/shop_settings_screen.dart`:
```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/error/error_messages.dart';
import '../../../core/router/screen_keys.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_button.dart';
import '../../../l10n/app_strings.dart';
import '../../auth/state/session.dart';
import '../../auth/state/session_controller.dart';
import '../api/shop_api.dart';
import '../state/shop_settings_controller.dart';

/// 매장 정보 화면. 사장은 이름·전화번호·주소를 고쳐 저장할 수 있고,
/// 직원은 읽기 전용으로 본다.
class ShopSettingsScreen extends ConsumerStatefulWidget {
  const ShopSettingsScreen({super.key});

  @override
  ConsumerState<ShopSettingsScreen> createState() =>
      _ShopSettingsScreenState();
}

class _ShopSettingsScreenState extends ConsumerState<ShopSettingsScreen> {
  final _nameController = TextEditingController();
  final _phoneController = TextEditingController();
  final _addressController = TextEditingController();
  bool _fieldsInitialized = false;
  bool _busy = false;
  String? _nameError;
  String? _errorText;
  String? _successText;

  int? get _shopId {
    final session = ref.read(sessionControllerProvider).value;
    return session is SignedIn ? session.selectedShopId : null;
  }

  void _initFields(ShopSettings settings) {
    if (_fieldsInitialized) return;
    _fieldsInitialized = true;
    _nameController.text = settings.name;
    _phoneController.text = settings.phone ?? '';
    _addressController.text = settings.address ?? '';
  }

  @override
  void dispose() {
    _nameController.dispose();
    _phoneController.dispose();
    _addressController.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    final shopId = _shopId;
    if (shopId == null) return;

    final name = _nameController.text.trim();
    if (name.isEmpty || name.length > 50) {
      setState(() => _nameError = AppStrings.shopNameRequired);
      return;
    }

    setState(() {
      _nameError = null;
      _errorText = null;
      _successText = null;
      _busy = true;
    });
    try {
      final phone = _phoneController.text.trim();
      final address = _addressController.text.trim();
      await ref.read(shopSettingsControllerProvider(shopId).notifier).save(
            name: name,
            phone: phone.isEmpty ? null : phone,
            address: address.isEmpty ? null : address,
          );
      if (!mounted) return;
      setState(() {
        _busy = false;
        _successText = AppStrings.saved;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _busy = false;
        _errorText = messageFor(e);
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final shopId = _shopId;
    final session = ref.watch(sessionControllerProvider).value;
    final isOwner =
        session is SignedIn && (session.selectedShop?.isOwner ?? false);
    final settingsAsync = shopId == null
        ? const AsyncValue<ShopSettings>.loading()
        : ref.watch(shopSettingsControllerProvider(shopId));

    return Scaffold(
      key: ScreenKeys.settingsShop,
      body: AppBackground(
        child: SafeArea(
          child: settingsAsync.when(
            data: (settings) {
              _initFields(settings);
              return SingleChildScrollView(
                padding: const EdgeInsets.all(AppSpacing.lg),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      AppStrings.settingsShopInfo,
                      style: AppTypography.titleKo,
                    ),
                    const SizedBox(height: AppSpacing.xl),
                    TextField(
                      controller: _nameController,
                      enabled: isOwner,
                      decoration: InputDecoration(
                        labelText: AppStrings.shopName,
                        errorText: _nameError,
                      ),
                    ),
                    const SizedBox(height: AppSpacing.md),
                    TextField(
                      controller: _phoneController,
                      enabled: isOwner,
                      decoration: const InputDecoration(
                        labelText: AppStrings.shopPhone,
                      ),
                    ),
                    const SizedBox(height: AppSpacing.md),
                    TextField(
                      controller: _addressController,
                      enabled: isOwner,
                      decoration: const InputDecoration(
                        labelText: AppStrings.shopAddress,
                      ),
                    ),
                    if (isOwner) ...[
                      const SizedBox(height: AppSpacing.xl),
                      AppButton(
                        label: AppStrings.save,
                        filled: true,
                        busy: _busy,
                        onPressed: _busy ? null : _save,
                      ),
                    ],
                    if (_errorText != null) ...[
                      const SizedBox(height: AppSpacing.lg),
                      Text(_errorText!, style: AppTypography.caption),
                    ],
                    if (_successText != null) ...[
                      const SizedBox(height: AppSpacing.lg),
                      Text(_successText!, style: AppTypography.caption),
                    ],
                  ],
                ),
              );
            },
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (error, _) => Center(
              child: Text(messageFor(error), style: AppTypography.body),
            ),
          ),
        ),
      ),
    );
  }
}
```

`app/lib/features/shop/state/shop_settings_controller.dart`:
```dart
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../auth/state/session_controller.dart';
import '../api/shop_api.dart';
import 'shop_errors.dart';
import 'shop_providers.dart';

/// 매장 하나의 정보. 매장 id로 만든 [shopSettingsControllerProvider]
/// family가 매장마다 별도 인스턴스를 준다.
class ShopSettingsController extends AsyncNotifier<ShopSettings> {
  ShopSettingsController(this.shopId);

  final int shopId;

  ShopApi get _api => ref.read(shopApiProvider);

  @override
  Future<ShopSettings> build() => _api.settings(shopId);

  Future<void> save({
    required String name,
    String? phone,
    String? address,
  }) {
    return runShopScoped(ref, () async {
      final updated = await _api.updateSettings(
        shopId,
        name: name,
        phone: phone,
        address: address,
      );
      state = AsyncData(updated);
      // 이름이 바뀌었을 수 있으니 본인 정보를 다시 불러와 홈의 매장 이름도
      // 갱신한다.
      await ref.read(sessionControllerProvider.notifier).reloadMe();
    });
  }
}

final shopSettingsControllerProvider = AsyncNotifierProvider.family<
    ShopSettingsController, ShopSettings, int>(
  ShopSettingsController.new,
);
```

- [ ] **Step 3: 통과를 확인하고 커밋한다**

Run: `flutter test && flutter analyze`
Expected: `All tests passed!` (새 테스트 5개), `No issues found!`

```bash
git add app/lib app/test
git commit -m "feat(app): 매장 정보 — 사장은 고치고 직원은 본다"
```

### Task 12: 계정 화면 — 로그인 수단 연결·해제, 로그아웃

**Files:**
- Create: `app/lib/features/account/api/account_api.dart`, `app/lib/features/account/state/account_controller.dart`, `app/lib/features/account/screens/account_screen.dart`
- Modify: `app/lib/core/router/app_router.dart`, `app/lib/core/router/placeholder_screens.dart`, `app/lib/l10n/app_strings.dart`, `app/test/support/fake_social_sign_in.dart`
- Test: `app/test/features/account/api/account_api_test.dart`, `app/test/features/account/state/account_controller_test.dart`, `app/test/features/account/screens/account_screen_test.dart`

**Interfaces:**
- Consumes: `ApiClient`·`TokenStore`(Task 4·5), `SocialCredential`·`SocialSignIn`·`socialSignInsProvider`·`sessionControllerProvider`(Task 6·8), `appConfigProvider`, 디자인 위젯
- Produces:
  - `AccountApi({required ApiClient client, required TokenStore tokenStore})`: `link(SocialCredential) → List<String>`, `unlink(String provider) → List<String>`, `withdraw({bool confirmCloseShops = false})` — Task 13·16 이 그대로 쓴다
  - `accountApiProvider`, 계정 컨트롤러와 `AccountScreen`(`/settings/account`)

동작 규칙 (점검표 S5)
- **해제 응답의 새 토큰을 다른 어떤 일보다 먼저 저장한다.** 서버는 해제하는 순간 그 유저의 모든 세션을 끊는다. 저장하기 전에 옛 토큰으로 요청이 나가면 401 → 갱신(죽은 리프레시 토큰) → 세션 종료가 된다. `AccountApi.unlink` 가 응답을 받자마자 저장하고, 컨트롤러는 그 뒤에 `reloadMe()` 를 부른다. 테스트가 "저장 → reloadMe" 순서를 못 박는다.
- 연결 요청의 본문에는 `display_name` 을 넣지 않는다(서버가 받지 않는다).
- 소셜 로그인이 `null`(취소)이면 요청을 보내지 않는다.
- 구글 수단 해제가 성공하면 구글 `SocialSignIn.disconnect()` 를 한 번 부른다. 실패해도 해제는 실패가 아니다.
- 수단이 하나뿐이면 "해제"를 끄고 이유를 적어 둔다(서버도 `LAST_IDENTITY` 로 막는다). 해제는 "다른 기기가 모두 로그아웃된다"는 확인 시트를 거친다.
- 소속이 없는 유저도 이 화면을 열 수 있다(Task 7 의 가드).

실험에서 걸린 함정 — 테스트를 쓸 때 그대로 지킨다
- 테스트에서 `ApiClient` 의 `dio` 와 `refreshDio` 에 **같은 `Dio` 인스턴스를 넘기면 무한 갱신 재귀**에 빠진다(갱신 요청도 인터셉터를 탄다). 언제나 따로 만든다.
- 위젯 테스트에서 `apiClientProvider` 만 가짜로 바꾸고 `tokenStoreProvider` 를 그대로 두면 `SecureTokenStore` 가 플랫폼 채널 예외를 던져 **조용히** 실패한다. 둘 다 바꾼다.
- 확인 시트가 열려 있어도 배경의 "해제" 글자는 트리에 남는다. `find.text('해제').last` 는 배경을 가리킬 수 있다 — 확정 버튼은 `AppButton` 이면서 `filled` 인 것으로 짚는다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`app/test/features/account/api/account_api_test.dart`:
```dart
// AccountApi를 실제 네트워크 없이(FakeHttpClientAdapter) 검증한다. Riverpod은
// 필요 없다 — API 클래스 하나만 직접 구성해서 쓴다.
import 'dart:convert';
import 'dart:typed_data';

import 'package:chagocnote/core/error/api_exception.dart';
import 'package:chagocnote/core/proxy/api_client.dart';
import 'package:chagocnote/core/storage/token_store.dart';
import 'package:chagocnote/features/account/api/account_api.dart';
import 'package:chagocnote/features/auth/api/social_sign_in.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/fake_http_client_adapter.dart';

AccountApi _build(FakeHandler handle, {TokenStore? tokenStore}) {
  final adapter = FakeHttpClientAdapter(handle);
  // 리프레시 요청은 별도의 Dio 인스턴스로 보내야 한다 — 같은 인스턴스를
  // 재사용하면 인터셉터를 함께 타서, 리프레시 요청 자체가 401을 받았을 때
  // 다시 리프레시를 시도하는 재귀에 빠진다(`ApiClient`의 문서 주석 참고).
  final dio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final refreshDio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final store = tokenStore ?? (MemoryTokenStore()
    ..save(access: 'old-access', refresh: 'old-refresh'));
  final client = ApiClient(tokenStore: store, dio: dio, refreshDio: refreshDio);
  return AccountApi(client: client, tokenStore: store);
}

void main() {
  group('link', () {
    test('display_name 없는 자격 증명은 그대로 본문으로 보내고 identities 를 돌려준다', () async {
      Map<String, dynamic>? sentBody;
      final api = _build((options, body) {
        sentBody = jsonDecode(utf8.decode(body!)) as Map<String, dynamic>;
        return const FakeResponse(
          statusCode: 200,
          data: {
            'identities': ['apple', 'kakao'],
          },
        );
      });

      final identities = await api.link(
        const SocialCredential(provider: 'kakao', token: 'tok'),
      );

      expect(sentBody, {'provider': 'kakao', 'token': 'tok'});
      expect(identities, ['apple', 'kakao']);
    });

    test('display_name 이 있는 자격 증명은 연결 요청 본문에서 뺀다', () async {
      Map<String, dynamic>? sentBody;
      final api = _build((options, body) {
        sentBody = jsonDecode(utf8.decode(body!)) as Map<String, dynamic>;
        return const FakeResponse(
          statusCode: 200,
          data: {
            'identities': ['apple'],
          },
        );
      });

      await api.link(
        const SocialCredential(
          provider: 'apple',
          token: 'tok',
          authorizationCode: 'code',
          nonce: 'nonce',
          displayName: '민석',
        ),
      );

      expect(sentBody, {
        'provider': 'apple',
        'token': 'tok',
        'authorization_code': 'code',
        'nonce': 'nonce',
      });
    });

    test('409 IDENTITY_ALREADY_LINKED 는 그대로 던진다', () async {
      final api = _build((options, body) {
        return const FakeResponse(
          statusCode: 409,
          data: {'code': 'IDENTITY_ALREADY_LINKED', 'message': '다른 계정'},
        );
      });

      await expectLater(
        api.link(const SocialCredential(provider: 'kakao', token: 'tok')),
        throwsA(
          isA<ApiException>().having((e) => e.code, 'code', 'IDENTITY_ALREADY_LINKED'),
        ),
      );
    });
  });

  group('unlink', () {
    test('응답의 새 토큰을 먼저 저장한 뒤 identities 를 돌려준다(S5)', () async {
      final store = MemoryTokenStore()
        ..save(access: 'old-access', refresh: 'old-refresh');
      final api = _build((options, body) {
        expect(options.method, 'DELETE');
        expect(options.path, '/v1/auth/identities/kakao');
        return const FakeResponse(
          statusCode: 200,
          data: {
            'identities': ['apple'],
            'access_token': 'new-access',
            'refresh_token': 'new-refresh',
            'token_type': 'Bearer',
            'expires_in': 3600,
          },
        );
      }, tokenStore: store);

      final identities = await api.unlink('kakao');

      expect(identities, ['apple']);
      expect(await store.readAccess(), 'new-access');
      expect(await store.readRefresh(), 'new-refresh');
    });

    test('404 IDENTITY_NOT_FOUND 는 토큰을 바꾸지 않고 그대로 던진다', () async {
      final store = MemoryTokenStore()
        ..save(access: 'old-access', refresh: 'old-refresh');
      final api = _build((options, body) {
        return const FakeResponse(
          statusCode: 404,
          data: {'code': 'IDENTITY_NOT_FOUND', 'message': '없음'},
        );
      }, tokenStore: store);

      await expectLater(
        api.unlink('kakao'),
        throwsA(isA<ApiException>().having((e) => e.code, 'code', 'IDENTITY_NOT_FOUND')),
      );
      expect(await store.readAccess(), 'old-access');
    });
  });

  group('withdraw', () {
    test('confirmCloseShops 가 false 면 본문 없이 보낸다', () async {
      Uint8List? sentBody;
      final api = _build((options, body) {
        expect(options.method, 'DELETE');
        expect(options.path, '/v1/auth/account');
        sentBody = body;
        return const FakeResponse(statusCode: 204);
      });

      await api.withdraw();

      expect(sentBody, isNull);
    });

    test('confirmCloseShops 가 true 면 JSON 불리언 본문을 보낸다', () async {
      Map<String, dynamic>? sentBody;
      String? contentType;
      final api = _build((options, body) {
        sentBody = jsonDecode(utf8.decode(body!)) as Map<String, dynamic>;
        contentType = options.headers['content-type'] as String?;
        return const FakeResponse(statusCode: 204);
      });

      await api.withdraw(confirmCloseShops: true);

      expect(sentBody, {'confirm_close_shops': true});
      expect(contentType, contains('application/json'));
    });

    test('204 는 정상 종료다', () async {
      final api = _build((options, body) => const FakeResponse(statusCode: 204));
      await api.withdraw();
    });

    test('401 은 이미 완료된 탈퇴로 보고 정상 종료한다(S12)', () async {
      final api = _build(
        (options, body) => const FakeResponse(
          statusCode: 401,
          data: {'code': 'UNAUTHENTICATED', 'message': '이미 탈퇴됨'},
        ),
      );

      await api.withdraw();
    });

    test('409 OWNERSHIP_TRANSFER_REQUIRED 는 그대로 던진다', () async {
      final api = _build(
        (options, body) => const FakeResponse(
          statusCode: 409,
          data: {'code': 'OWNERSHIP_TRANSFER_REQUIRED', 'message': '소유권 이전 필요'},
        ),
      );

      await expectLater(
        api.withdraw(),
        throwsA(
          isA<ApiException>().having(
            (e) => e.code,
            'code',
            'OWNERSHIP_TRANSFER_REQUIRED',
          ),
        ),
      );
    });

    test('409 SHOP_CLOSE_CONFIRM_REQUIRED 는 그대로 던진다', () async {
      final api = _build(
        (options, body) => const FakeResponse(
          statusCode: 409,
          data: {'code': 'SHOP_CLOSE_CONFIRM_REQUIRED', 'message': '매장 닫힘 확인 필요'},
        ),
      );

      await expectLater(
        api.withdraw(),
        throwsA(
          isA<ApiException>().having(
            (e) => e.code,
            'code',
            'SHOP_CLOSE_CONFIRM_REQUIRED',
          ),
        ),
      );
    });
  });
}
```

`app/test/features/account/screens/account_screen_test.dart`:
```dart
// 계정 화면을 실제 라우터 + 가짜 HTTP 어댑터로 검증한다. 매장 설정 화면
// 테스트와 같은 방식(FakeSessionGateway + apiClientProvider 를 가짜 어댑터로
// 문 실제 AccountApi/AccountController)을 쓴다.
import 'package:chagocnote/core/proxy/api_client.dart';
import 'package:chagocnote/core/proxy/providers.dart';
import 'package:chagocnote/core/router/app_router.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/core/storage/token_store.dart';
import 'package:chagocnote/design/app_theme.dart';
import 'package:chagocnote/design/bridge/glass_surface.dart';
import 'package:chagocnote/design/widgets/app_button.dart';
import 'package:chagocnote/design/widgets/app_glass_card.dart';
import 'package:chagocnote/features/auth/api/social_sign_in.dart';
import 'package:chagocnote/features/auth/state/session.dart';
import 'package:chagocnote/features/auth/state/session_controller.dart';
import 'package:chagocnote/features/auth/state/social_sign_ins.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/fake_http_client_adapter.dart';
import '../../../support/fake_session_gateway.dart';
import '../../../support/fake_social_sign_in.dart';

Me _me(List<String> identities) => Me(
      id: 1,
      displayName: '민석',
      profileImageUrl: null,
      identities: identities,
      shops: const [],
    );

String _labelFor(String provider) => switch (provider) {
      'kakao' => AppStrings.providerKakao,
      'google' => AppStrings.providerGoogle,
      'apple' => AppStrings.providerApple,
      'dev' => AppStrings.providerDev,
      _ => provider,
    };

/// [provider] 행의 해제 버튼. 화면에 로그인 수단마다 같은 "해제" 라벨이
/// 반복되므로, provider 라벨(카카오 등)을 담은 카드 안에서만 찾는다.
Finder _unlinkRowButton(String provider) => find.descendant(
      of: find.ancestor(
        of: find.text(_labelFor(provider)),
        matching: find.byType(AppGlassCard),
      ),
      matching: find.text(AppStrings.unlink),
    );

/// 해제 확인 시트의 확정 버튼. 행의 해제 버튼과 라벨이 같아서(`filled`만
/// 다르다) 위젯 속성으로 구분한다.
final Finder _confirmUnlinkButton = find.byWidgetPredicate(
  (widget) => widget is AppButton && widget.label == AppStrings.unlink && widget.filled,
);

({ProviderContainer container, FakeHttpClientAdapter adapter}) _setUp(
  FakeSessionGateway gateway,
  FakeHandler handle, {
  List<FakeSocialSignIn> signIns = const [],
}) {
  final adapter = FakeHttpClientAdapter(handle);
  // 리프레시 요청은 별도의 Dio 인스턴스로 보내야 한다 — 같은 인스턴스를
  // 재사용하면 리프레시 요청 자체가 401을 받았을 때 다시 리프레시를
  // 시도하는 재귀에 빠진다.
  final dio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final refreshDio = Dio(BaseOptions())..httpClientAdapter = adapter;
  // `accountApiProvider`는 `apiClientProvider`와 별개로 `tokenStoreProvider`를
  // 직접 읽는다 — 오버라이드하지 않으면 실제 `SecureTokenStore`(플랫폼
  // 채널)로 떨어져 테스트에서 던진다.
  final tokenStore = _NoopTokenStore();
  final container = ProviderContainer.test(
    retry: (retryCount, error) => null,
    overrides: [
      sessionGatewayProvider.overrideWithValue(gateway),
      socialSignInsProvider.overrideWithValue(signIns),
      tokenStoreProvider.overrideWithValue(tokenStore),
      apiClientProvider.overrideWith(
        (ref) => ApiClient(
          tokenStore: tokenStore,
          dio: dio,
          refreshDio: refreshDio,
          onSessionEnded: ref.read(sessionEndedSignalProvider).fire,
        ),
      ),
    ],
  );
  return (container: container, adapter: adapter);
}

Widget _appWith(ProviderContainer container) {
  return UncontrolledProviderScope(
    container: container,
    child: Consumer(
      builder: (context, ref, _) {
        final router = ref.watch(routerProvider);
        return MaterialApp.router(
          routerConfig: router,
          theme: appTheme(),
          builder: (context, child) => GlassBridge(
            factory: const OpaqueSurfaceFactory(),
            child: child!,
          ),
        );
      },
    ),
  );
}

void main() {
  testWidgets('매장이 없는 사용자도 계정 화면을 열 수 있고, 로그인 수단이 하나면 해제 버튼 대신 안내를 보여준다', (
    tester,
  ) async {
    final gateway = FakeSessionGateway()..meOnRestore = _me(['apple']);
    final setup = _setUp(
      gateway,
      (options, body) => fail('예상하지 못한 요청: ${options.path}'),
    );
    addTearDown(setup.container.dispose);

    await tester.pumpWidget(_appWith(setup.container));
    await tester.pumpAndSettle();
    setup.container.read(routerProvider).go('/settings/account');
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.settingsAccount), findsOneWidget);
    expect(find.text(AppStrings.unlink), findsNothing);
    expect(find.text(AppStrings.unlinkOnlyOneCaption), findsOneWidget);
  });

  testWidgets('해제 확인 시트를 취소하면 요청을 보내지 않는다', (tester) async {
    final gateway = FakeSessionGateway()..meOnRestore = _me(['apple', 'kakao']);
    final setup = _setUp(
      gateway,
      (options, body) => fail('예상하지 못한 요청: ${options.path}'),
    );
    addTearDown(setup.container.dispose);

    await tester.pumpWidget(_appWith(setup.container));
    await tester.pumpAndSettle();
    setup.container.read(routerProvider).go('/settings/account');
    await tester.pumpAndSettle();

    await tester.tap(_unlinkRowButton('kakao'));
    await tester.pumpAndSettle();
    expect(find.text(AppStrings.unlinkConfirmMessage), findsOneWidget);

    await tester.tap(find.text(AppStrings.cancel));
    await tester.pumpAndSettle();

    expect(setup.adapter.requests, isEmpty);
  });

  testWidgets('해제를 확정하면 DELETE 요청을 보내고 목록을 갱신한다', (tester) async {
    final gateway = FakeSessionGateway()
      ..meOnRestore = _me(['apple', 'kakao'])
      ..meOnRefresh = _me(['apple']);
    final setup = _setUp(gateway, (options, body) {
      expect(options.method, 'DELETE');
      expect(options.path, '/v1/auth/identities/kakao');
      return const FakeResponse(
        statusCode: 200,
        data: {
          'identities': ['apple'],
          'access_token': 'new-access',
          'refresh_token': 'new-refresh',
          'token_type': 'Bearer',
          'expires_in': 3600,
        },
      );
    });
    addTearDown(setup.container.dispose);

    await tester.pumpWidget(_appWith(setup.container));
    await tester.pumpAndSettle();
    setup.container.read(routerProvider).go('/settings/account');
    await tester.pumpAndSettle();

    await tester.tap(_unlinkRowButton('kakao'));
    await tester.pumpAndSettle();
    await tester.tap(_confirmUnlinkButton);
    await tester.pumpAndSettle();

    expect(setup.adapter.requests, hasLength(1));
    expect(gateway.refreshMeCallCount, 1);
    expect(find.text(AppStrings.unlinkOnlyOneCaption), findsOneWidget);
  });

  testWidgets('연결 요청이 IDENTITY_ALREADY_LINKED 를 받으면 문구를 보여준다', (tester) async {
    final gateway = FakeSessionGateway()..meOnRestore = _me(['apple']);
    final kakao = FakeSocialSignIn('kakao')
      ..credentialToReturn = const SocialCredential(provider: 'kakao', token: 'tok');
    final setup = _setUp(
      gateway,
      (options, body) => const FakeResponse(
        statusCode: 409,
        data: {'code': 'IDENTITY_ALREADY_LINKED', 'message': '다른 계정'},
      ),
      signIns: [kakao],
    );
    addTearDown(setup.container.dispose);

    await tester.pumpWidget(_appWith(setup.container));
    await tester.pumpAndSettle();
    setup.container.read(routerProvider).go('/settings/account');
    await tester.pumpAndSettle();

    await tester.tap(find.text(AppStrings.providerKakao));
    await tester.pumpAndSettle();

    expect(find.text('다른 계정에 연결된 로그인 수단입니다.'), findsOneWidget);
  });

  testWidgets('해제 확정이 LAST_IDENTITY 를 받으면 문구를 보여주고 목록은 그대로다', (tester) async {
    final gateway = FakeSessionGateway()..meOnRestore = _me(['apple', 'kakao']);
    final setup = _setUp(
      gateway,
      (options, body) => const FakeResponse(
        statusCode: 409,
        data: {'code': 'LAST_IDENTITY', 'message': '마지막 수단'},
      ),
    );
    addTearDown(setup.container.dispose);

    await tester.pumpWidget(_appWith(setup.container));
    await tester.pumpAndSettle();
    setup.container.read(routerProvider).go('/settings/account');
    await tester.pumpAndSettle();

    await tester.tap(_unlinkRowButton('kakao'));
    await tester.pumpAndSettle();
    await tester.tap(_confirmUnlinkButton);
    await tester.pumpAndSettle();

    expect(find.text('마지막 로그인 수단은 해제할 수 없습니다.'), findsOneWidget);
    expect(gateway.refreshMeCallCount, 0);
  });

  testWidgets('로그아웃하면 로그인 화면으로 간다', (tester) async {
    final gateway = FakeSessionGateway()..meOnRestore = _me(['apple']);
    final setup = _setUp(
      gateway,
      (options, body) => fail('예상하지 못한 요청: ${options.path}'),
    );
    addTearDown(setup.container.dispose);

    await tester.pumpWidget(_appWith(setup.container));
    await tester.pumpAndSettle();
    setup.container.read(routerProvider).go('/settings/account');
    await tester.pumpAndSettle();

    await tester.tap(find.text(AppStrings.logout));
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.login), findsOneWidget);
    expect(gateway.signOutCalled, isTrue);
  });
}

class _NoopTokenStore implements TokenStore {
  @override
  Future<void> clear() async {}

  @override
  Future<String?> readAccess() async => null;

  @override
  Future<String?> readRefresh() async => null;

  @override
  Future<void> save({required String access, required String refresh}) async {}
}
```

`app/test/features/account/state/account_controller_test.dart`:
```dart
// AccountController을 위젯 트리 없이 ProviderContainer로 직접 검증한다.
// SessionGateway는 FakeSessionGateway, HTTP는 FakeHttpClientAdapter를 문
// 실제 AccountApi/AccountController로 확인한다.
import 'package:chagocnote/core/proxy/api_client.dart';
import 'package:chagocnote/core/proxy/providers.dart';
import 'package:chagocnote/core/storage/token_store.dart';
import 'package:chagocnote/features/account/state/account_controller.dart';
import 'package:chagocnote/features/auth/api/social_sign_in.dart';
import 'package:chagocnote/features/auth/state/session.dart';
import 'package:chagocnote/features/auth/state/session_controller.dart';
import 'package:chagocnote/features/auth/state/social_sign_ins.dart';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/fake_http_client_adapter.dart';
import '../../../support/fake_session_gateway.dart';
import '../../../support/fake_social_sign_in.dart';

Me _me(List<String> identities) => Me(
      id: 1,
      displayName: '민석',
      profileImageUrl: null,
      identities: identities,
      shops: const [],
    );

/// save()가 불릴 때마다 [order]에 'save'를 남기는 토큰 저장소. 실제 값은
/// 내부의 [MemoryTokenStore]에 그대로 위임한다.
class _OrderTrackingTokenStore implements TokenStore {
  _OrderTrackingTokenStore(this.order);

  final List<String> order;
  final _inner = MemoryTokenStore();

  @override
  Future<void> save({required String access, required String refresh}) async {
    order.add('save');
    await _inner.save(access: access, refresh: refresh);
  }

  @override
  Future<String?> readAccess() => _inner.readAccess();

  @override
  Future<String?> readRefresh() => _inner.readRefresh();

  @override
  Future<void> clear() => _inner.clear();
}

/// refreshMe()가 불릴 때마다 [order]에 'reloadMe'를 남기는 세션 게이트웨이.
class _OrderTrackingGateway extends FakeSessionGateway {
  _OrderTrackingGateway(this.order);

  final List<String> order;

  @override
  Future<Me> refreshMe() async {
    order.add('reloadMe');
    return super.refreshMe();
  }
}

({ProviderContainer container, FakeHttpClientAdapter adapter, TokenStore tokenStore})
    _setUp({
  required FakeSessionGateway gateway,
  required FakeHandler handle,
  List<FakeSocialSignIn> signIns = const [],
  TokenStore? tokenStore,
}) {
  final adapter = FakeHttpClientAdapter(handle);
  final dio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final store = tokenStore ?? MemoryTokenStore();
  final container = ProviderContainer.test(
    retry: (retryCount, error) => null,
    overrides: [
      sessionGatewayProvider.overrideWithValue(gateway),
      socialSignInsProvider.overrideWithValue(signIns),
      tokenStoreProvider.overrideWithValue(store),
      apiClientProvider.overrideWith(
        (ref) => ApiClient(
          tokenStore: store,
          dio: dio,
          refreshDio: dio,
          onSessionEnded: ref.read(sessionEndedSignalProvider).fire,
        ),
      ),
    ],
  );
  return (container: container, adapter: adapter, tokenStore: store);
}

void main() {
  test('취소된 소셜 로그인은 요청을 보내지 않는다', () async {
    final gateway = FakeSessionGateway()..meOnRestore = _me(['apple']);
    final kakao = FakeSocialSignIn('kakao')..credentialToReturn = null;
    final setup = _setUp(
      gateway: gateway,
      signIns: [kakao],
      handle: (options, body) => fail('예상하지 못한 요청: ${options.path}'),
    );
    addTearDown(setup.container.dispose);
    await setup.container.read(sessionControllerProvider.future);

    await setup.container.read(accountControllerProvider.notifier).link(kakao);

    expect(kakao.signInCallCount, 1);
    expect(setup.adapter.requests, isEmpty);
    expect(gateway.refreshMeCallCount, 0);
  });

  test('로그인 성공하면 연결 요청 후 reloadMe 를 부른다', () async {
    final gateway = FakeSessionGateway()
      ..meOnRestore = _me(['apple'])
      ..meOnRefresh = _me(['apple', 'kakao']);
    final kakao = FakeSocialSignIn('kakao')
      ..credentialToReturn = const SocialCredential(provider: 'kakao', token: 'tok');
    final setup = _setUp(
      gateway: gateway,
      signIns: [kakao],
      handle: (options, body) {
        expect(options.method, 'POST');
        expect(options.path, '/v1/auth/identities');
        return const FakeResponse(
          statusCode: 200,
          data: {
            'identities': ['apple', 'kakao'],
          },
        );
      },
    );
    addTearDown(setup.container.dispose);
    await setup.container.read(sessionControllerProvider.future);

    await setup.container.read(accountControllerProvider.notifier).link(kakao);

    expect(setup.adapter.requests, hasLength(1));
    expect(gateway.refreshMeCallCount, 1);
  });

  test('개발용 연결은 이름을 dev 자격 증명으로 보낸다', () async {
    final gateway = FakeSessionGateway()
      ..meOnRestore = _me(['apple'])
      ..meOnRefresh = _me(['apple', 'dev']);
    Map<String, dynamic>? sentBody;
    final setup = _setUp(
      gateway: gateway,
      handle: (options, body) {
        sentBody = {'provider': 'dev', 'token': '민석'};
        return const FakeResponse(
          statusCode: 200,
          data: {
            'identities': ['apple', 'dev'],
          },
        );
      },
    );
    addTearDown(setup.container.dispose);
    await setup.container.read(sessionControllerProvider.future);

    await setup.container.read(accountControllerProvider.notifier).linkDev('민석');

    expect(sentBody, {'provider': 'dev', 'token': '민석'});
    expect(gateway.refreshMeCallCount, 1);
  });

  test('해제하면 토큰을 먼저 저장한 뒤에 reloadMe 를 부른다(S5 순서 고정)', () async {
    final order = <String>[];
    final gateway = _OrderTrackingGateway(order)
      ..meOnRestore = _me(['apple', 'kakao'])
      ..meOnRefresh = _me(['apple']);
    final setup = _setUp(
      gateway: gateway,
      tokenStore: _OrderTrackingTokenStore(order),
      handle: (options, body) {
        expect(options.method, 'DELETE');
        expect(options.path, '/v1/auth/identities/kakao');
        return const FakeResponse(
          statusCode: 200,
          data: {
            'identities': ['apple'],
            'access_token': 'new-access',
            'refresh_token': 'new-refresh',
            'token_type': 'Bearer',
            'expires_in': 3600,
          },
        );
      },
    );
    addTearDown(setup.container.dispose);
    await setup.container.read(sessionControllerProvider.future);

    await setup.container.read(accountControllerProvider.notifier).unlink('kakao');

    expect(order, ['save', 'reloadMe']);
    expect(await setup.tokenStore.readAccess(), 'new-access');
  });

  test('구글 해제 후 disconnect() 를 한 번 부른다', () async {
    final gateway = FakeSessionGateway()
      ..meOnRestore = _me(['apple', 'google'])
      ..meOnRefresh = _me(['apple']);
    final google = FakeSocialSignIn('google');
    final setup = _setUp(
      gateway: gateway,
      signIns: [google],
      handle: (options, body) => const FakeResponse(
        statusCode: 200,
        data: {
          'identities': ['apple'],
          'access_token': 'new-access',
          'refresh_token': 'new-refresh',
          'token_type': 'Bearer',
          'expires_in': 3600,
        },
      ),
    );
    addTearDown(setup.container.dispose);
    await setup.container.read(sessionControllerProvider.future);

    await setup.container.read(accountControllerProvider.notifier).unlink('google');

    expect(google.disconnectCallCount, 1);
  });

  test('disconnect() 가 던져도 해제 자체는 실패하지 않는다', () async {
    final gateway = FakeSessionGateway()
      ..meOnRestore = _me(['apple', 'google'])
      ..meOnRefresh = _me(['apple']);
    final google = FakeSocialSignIn('google')
      ..disconnectError = Exception('연결 끊기 실패');
    final setup = _setUp(
      gateway: gateway,
      signIns: [google],
      handle: (options, body) => const FakeResponse(
        statusCode: 200,
        data: {
          'identities': ['apple'],
          'access_token': 'new-access',
          'refresh_token': 'new-refresh',
          'token_type': 'Bearer',
          'expires_in': 3600,
        },
      ),
    );
    addTearDown(setup.container.dispose);
    await setup.container.read(sessionControllerProvider.future);

    await setup.container.read(accountControllerProvider.notifier).unlink('google');

    expect(google.disconnectCallCount, 1);
  });

  test('로그아웃하면 세션 게이트웨이의 signOut 을 부른다', () async {
    final gateway = FakeSessionGateway()..meOnRestore = _me(['apple']);
    final setup = _setUp(
      gateway: gateway,
      handle: (options, body) => fail('예상하지 못한 요청: ${options.path}'),
    );
    addTearDown(setup.container.dispose);
    await setup.container.read(sessionControllerProvider.future);

    await setup.container.read(accountControllerProvider.notifier).logout();

    expect(gateway.signOutCalled, isTrue);
  });
}
```

`app/test/support/fake_social_sign_in.dart` — 바꾼다:
```diff
--- a/test/support/fake_social_sign_in.dart
+++ b/test/support/fake_social_sign_in.dart
@@ -12,6 +12,11 @@ class FakeSocialSignIn implements SocialSignIn {
   SocialCredential? credentialToReturn;
   Object? signInError;
 
+  /// disconnect() 가 호출된 횟수. 계정 화면의 구글 해제 후 베스트 에포트
+  /// 연결 끊기를 검증하는 데 쓴다.
+  int disconnectCallCount = 0;
+  Object? disconnectError;
+
   @override
   Future<SocialCredential?> signIn() async {
     signInCallCount++;
@@ -20,5 +25,8 @@ class FakeSocialSignIn implements SocialSignIn {
   }
 
   @override
-  Future<void> disconnect() async {}
+  Future<void> disconnect() async {
+    disconnectCallCount++;
+    if (disconnectError != null) throw disconnectError!;
+  }
 }
```

Run: `flutter test test/features/account`
Expected: FAIL — `account_api.dart` 가 없다.

- [ ] **Step 2: 구현한다**

`app/lib/core/router/app_router.dart` — 바꾼다:
```diff
--- a/lib/core/router/app_router.dart
+++ b/lib/core/router/app_router.dart
@@ -2,6 +2,7 @@ import 'package:flutter/foundation.dart';
 import 'package:flutter_riverpod/flutter_riverpod.dart';
 import 'package:go_router/go_router.dart';
 
+import '../../features/account/screens/account_screen.dart';
 import '../../features/auth/screens/invite_code_screen.dart';
 import '../../features/auth/screens/login_screen.dart';
 import '../../features/auth/screens/shop_select_screen.dart';
@@ -87,7 +88,7 @@ final routerProvider = Provider<GoRouter>((ref) {
       ),
       GoRoute(
         path: '/settings/account',
-        builder: (context, state) => const SettingsAccountScreen(),
+        builder: (context, state) => const AccountScreen(),
       ),
       GoRoute(
         path: '/settings/account/withdraw',
```

`app/lib/core/router/placeholder_screens.dart` — 바꾼다:
```diff
--- a/lib/core/router/placeholder_screens.dart
+++ b/lib/core/router/placeholder_screens.dart
@@ -16,16 +16,6 @@ class _PlaceholderScreen extends StatelessWidget {
   }
 }
 
-class SettingsAccountScreen extends StatelessWidget {
-  const SettingsAccountScreen({super.key});
-
-  @override
-  Widget build(BuildContext context) => const _PlaceholderScreen(
-        label: 'settings_account',
-        screenKey: ScreenKeys.settingsAccount,
-      );
-}
-
 class SettingsAccountWithdrawScreen extends StatelessWidget {
   const SettingsAccountWithdrawScreen({super.key});
 
```

`app/lib/features/account/api/account_api.dart`:
```dart
import '../../../core/error/api_exception.dart';
import '../../../core/proxy/api_client.dart';
import '../../../core/storage/token_store.dart';
import '../../auth/api/social_sign_in.dart';

/// 계정 화면 전용 API — 로그인 수단 연결/해제, 회원 탈퇴.
class AccountApi {
  AccountApi({required this._client, required this._tokenStore});

  final ApiClient _client;
  final TokenStore _tokenStore;

  /// 로그인 수단을 연결한다. `display_name`은 로그인(가입)에서만 쓰는
  /// 필드라 연결 요청 본문에서는 뺀다.
  Future<List<String>> link(SocialCredential credential) async {
    final body = credential.toJson()..remove('display_name');
    final data = await _client.post('/v1/auth/identities', data: body)
        as Map<String, dynamic>;
    return (data['identities'] as List).cast<String>();
  }

  /// 로그인 수단을 해제한다. 서버가 이 순간 발급하는 토큰이 유일하게 유효한
  /// 토큰이 되므로(다른 모든 세션은 폐기된다), 다른 무엇을 하기도 전에
  /// 가장 먼저 저장한다(S5) — 그다음에야 `identities`를 돌려준다.
  Future<List<String>> unlink(String provider) async {
    final data = await _client.delete('/v1/auth/identities/$provider')
        as Map<String, dynamic>;
    await _tokenStore.save(
      access: data['access_token'] as String,
      refresh: data['refresh_token'] as String,
    );
    return (data['identities'] as List).cast<String>();
  }

  /// 회원 탈퇴. 경합하는 두 번째 요청이 401을 받는 것도(이미 다른 요청이
  /// 탈퇴를 완료시킨 것) 성공으로 취급한다(S12) — 그 외 오류는 그대로
  /// 던진다.
  Future<void> withdraw({bool confirmCloseShops = false}) async {
    try {
      await _client.delete(
        '/v1/auth/account',
        data: confirmCloseShops ? {'confirm_close_shops': true} : null,
      );
    } on ApiException catch (e) {
      if (e.statusCode == 401) return;
      rethrow;
    }
  }
}
```

`app/lib/features/account/screens/account_screen.dart`:
```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/error/error_messages.dart';
import '../../../core/proxy/providers.dart';
import '../../../core/router/screen_keys.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_button.dart';
import '../../../design/widgets/app_glass_card.dart';
import '../../../design/widgets/app_sheet.dart';
import '../../../l10n/app_strings.dart';
import '../../auth/api/social_sign_in.dart';
import '../../auth/state/session.dart';
import '../../auth/state/session_controller.dart';
import '../../auth/state/social_sign_ins.dart';
import '../state/account_controller.dart';

/// 계정 화면 — 로그인 수단 연결/해제, 로그아웃, 회원 탈퇴로 가는 입구.
class AccountScreen extends ConsumerStatefulWidget {
  const AccountScreen({super.key});

  @override
  ConsumerState<AccountScreen> createState() => _AccountScreenState();
}

class _AccountScreenState extends ConsumerState<AccountScreen> {
  final _devNameController = TextEditingController();
  bool _busy = false;
  String? _errorText;
  String? _devNameError;

  @override
  void dispose() {
    _devNameController.dispose();
    super.dispose();
  }

  Future<void> _run(Future<void> Function() action) async {
    setState(() {
      _busy = true;
      _errorText = null;
    });
    try {
      await action();
      if (!mounted) return;
      setState(() => _busy = false);
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _busy = false;
        _errorText = messageFor(e);
      });
    }
  }

  Future<void> _link(SocialSignIn signIn) =>
      _run(() => ref.read(accountControllerProvider.notifier).link(signIn));

  Future<void> _linkDev() {
    final name = _devNameController.text.trim();
    if (name.isEmpty) {
      setState(() => _devNameError = AppStrings.devNameRequired);
      return Future.value();
    }
    setState(() => _devNameError = null);
    return _run(
      () => ref.read(accountControllerProvider.notifier).linkDev(name),
    );
  }

  Future<void> _confirmUnlink(String provider) async {
    final confirmed = await AppSheet.show<bool>(
      context,
      builder: (context) => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            AppStrings.unlinkConfirmMessage,
            style: AppTypography.body,
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: AppSpacing.lg),
          AppButton(
            label: AppStrings.unlink,
            filled: true,
            onPressed: () => Navigator.of(context).pop(true),
          ),
          const SizedBox(height: AppSpacing.sm),
          AppButton(
            label: AppStrings.cancel,
            onPressed: () => Navigator.of(context).pop(false),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;
    await _run(
      () => ref.read(accountControllerProvider.notifier).unlink(provider),
    );
  }

  Future<void> _logout() =>
      _run(() => ref.read(accountControllerProvider.notifier).logout());

  String _labelFor(String provider) => switch (provider) {
        'kakao' => AppStrings.providerKakao,
        'google' => AppStrings.providerGoogle,
        'apple' => AppStrings.providerApple,
        'dev' => AppStrings.providerDev,
        _ => provider,
      };

  @override
  Widget build(BuildContext context) {
    final session = ref.watch(sessionControllerProvider).value;
    final displayName = session is SignedIn ? session.me.displayName : '';
    final identities = ref.watch(accountIdentitiesProvider);
    final signIns = ref.watch(socialSignInsProvider);
    final config = ref.watch(appConfigProvider);
    final linkable =
        signIns.where((s) => !identities.contains(s.provider)).toList();
    final showDevLink = config.isDev && !identities.contains('dev');

    return Scaffold(
      key: ScreenKeys.settingsAccount,
      body: AppBackground(
        child: SafeArea(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(AppSpacing.lg),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(displayName, style: AppTypography.titleKo),
                const SizedBox(height: AppSpacing.xl),
                Text(
                  AppStrings.accountLinkedMethods,
                  style: AppTypography.caption,
                ),
                const SizedBox(height: AppSpacing.sm),
                for (final provider in identities)
                  Padding(
                    padding: const EdgeInsets.only(bottom: AppSpacing.sm),
                    child: AppGlassCard(
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(_labelFor(provider), style: AppTypography.body),
                          if (identities.length <= 1)
                            Text(
                              AppStrings.unlinkOnlyOneCaption,
                              style: AppTypography.caption,
                            )
                          else
                            AppButton(
                              label: AppStrings.unlink,
                              busy: _busy,
                              onPressed:
                                  _busy ? null : () => _confirmUnlink(provider),
                            ),
                        ],
                      ),
                    ),
                  ),
                if (linkable.isNotEmpty || showDevLink) ...[
                  const SizedBox(height: AppSpacing.xl),
                  Text(
                    AppStrings.accountAddMethod,
                    style: AppTypography.caption,
                  ),
                  const SizedBox(height: AppSpacing.sm),
                  for (final signIn in linkable) ...[
                    SizedBox(
                      width: double.infinity,
                      child: AppButton(
                        label: _labelFor(signIn.provider),
                        busy: _busy,
                        onPressed: _busy ? null : () => _link(signIn),
                      ),
                    ),
                    const SizedBox(height: AppSpacing.sm),
                  ],
                  if (showDevLink) ...[
                    TextField(
                      controller: _devNameController,
                      decoration: InputDecoration(
                        labelText: AppStrings.devNameLabel,
                        errorText: _devNameError,
                      ),
                    ),
                    const SizedBox(height: AppSpacing.sm),
                    SizedBox(
                      width: double.infinity,
                      child: AppButton(
                        label: AppStrings.devSignIn,
                        busy: _busy,
                        onPressed: _busy ? null : _linkDev,
                      ),
                    ),
                  ],
                ],
                const SizedBox(height: AppSpacing.xl),
                AppButton(
                  label: AppStrings.logout,
                  onPressed: _busy ? null : _logout,
                ),
                const SizedBox(height: AppSpacing.sm),
                AppButton(
                  label: AppStrings.withdraw,
                  onPressed: () => context.push('/settings/account/withdraw'),
                ),
                if (_errorText != null) ...[
                  const SizedBox(height: AppSpacing.lg),
                  Text(_errorText!, style: AppTypography.caption),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}
```

`app/lib/features/account/state/account_controller.dart`:
```dart
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/proxy/providers.dart';
import '../../auth/api/social_sign_in.dart';
import '../../auth/state/session.dart';
import '../../auth/state/session_controller.dart';
import '../../auth/state/social_sign_ins.dart';
import '../api/account_api.dart';

final accountApiProvider = Provider<AccountApi>(
  (ref) => AccountApi(
    client: ref.watch(apiClientProvider),
    tokenStore: ref.watch(tokenStoreProvider),
  ),
);

/// 현재 로그인 수단 목록. 세션의 `Me.identities`를 그대로 노출한다.
final accountIdentitiesProvider = Provider<List<String>>((ref) {
  final session = ref.watch(sessionControllerProvider).value;
  return session is SignedIn ? session.me.identities : const [];
});

/// 계정 화면의 동작(연결/해제/로그아웃)을 담당한다. 화면에 보여줄 상태는
/// [accountIdentitiesProvider]와 `sessionControllerProvider`에서 직접
/// 읽으므로, 이 컨트롤러는 별도의 데이터 상태를 갖지 않는다.
class AccountController extends Notifier<AsyncValue<void>> {
  AccountApi get _api => ref.read(accountApiProvider);

  SessionController get _session =>
      ref.read(sessionControllerProvider.notifier);

  @override
  AsyncValue<void> build() => const AsyncData(null);

  /// [signIn]으로 새 로그인 수단을 연결한다. 사용자가 취소하면(`null`)
  /// 요청을 보내지 않는다.
  Future<void> link(SocialSignIn signIn) async {
    final credential = await signIn.signIn();
    if (credential == null) return;
    await _api.link(credential);
    await _session.reloadMe();
  }

  /// 개발용 로그인 수단을 이름으로 연결한다.
  Future<void> linkDev(String name) async {
    await _api.link(SocialCredential(provider: 'dev', token: name));
    await _session.reloadMe();
  }

  /// [provider]를 해제한다. 해제 응답의 새 토큰은 `AccountApi.unlink` 안에서
  /// 이미 저장되었으므로, 그다음에 본인 정보를 다시 불러온다. 구글이었다면
  /// 마지막으로 구글 SDK 연결도 끊는다(베스트 에포트).
  Future<void> unlink(String provider) async {
    await _api.unlink(provider);
    await _session.reloadMe();
    if (provider == 'google') {
      await _disconnectGoogle();
    }
  }

  Future<void> _disconnectGoogle() async {
    for (final signIn in ref.read(socialSignInsProvider)) {
      if (signIn.provider != 'google') continue;
      try {
        await signIn.disconnect();
      } catch (_) {
        // 베스트 에포트 — 해제 자체는 이미 서버에서 끝났다.
      }
      return;
    }
  }

  Future<void> logout() => _session.signOut();
}

final accountControllerProvider =
    NotifierProvider<AccountController, AsyncValue<void>>(
  AccountController.new,
);
```

`app/lib/l10n/app_strings.dart` — 바꾼다:
```diff
--- a/lib/l10n/app_strings.dart
+++ b/lib/l10n/app_strings.dart
@@ -66,4 +66,16 @@ class AppStrings {
   static const save = '저장';
   static const saved = '저장했습니다';
   static const shopNameRequired = '매장 이름을 입력해 주세요.';
+
+  // 계정
+  static const providerKakao = '카카오';
+  static const providerGoogle = 'Google';
+  static const providerApple = 'Apple';
+  static const providerDev = '개발용';
+  static const accountLinkedMethods = '로그인 수단';
+  static const accountAddMethod = '로그인 수단 추가';
+  static const unlink = '해제';
+  static const unlinkOnlyOneCaption = '마지막 로그인 수단은 해제할 수 없습니다.';
+  static const unlinkConfirmMessage = '해제하면 다른 모든 기기에서 로그아웃됩니다.';
+  static const withdraw = '회원 탈퇴';
 }
```

- [ ] **Step 3: 통과와 판별력을 확인한다**

Run: `flutter test && flutter analyze`
Expected: `All tests passed!` (새 테스트 24개), `No issues found!`

`account_api.dart` 의 `unlink` 에서 토큰 저장 줄을 `return` 뒤로 옮길 수는 없으니, 대신 저장 줄을 잠깐 지우고 `flutter test test/features/account` 를 돌린다 — `응답의 새 토큰을 먼저 저장한 뒤 identities 를 돌려준다(S5)` 와 순서를 고정한 컨트롤러 테스트가 실패해야 한다. 확인한 뒤 되돌린다.

- [ ] **Step 4: 커밋**

```bash
git add app/lib app/test
git commit -m "feat(app): 계정 화면 — 해제 응답의 새 토큰을 먼저 저장한다"
```

### Task 13: 회원 탈퇴

**Files:**
- Create: `app/lib/features/account/state/withdraw_controller.dart`, `app/lib/features/account/screens/withdraw_screen.dart`
- Modify: `app/lib/features/auth/state/session_gateway.dart`(`clearLocal()`), `app/lib/features/auth/state/session_controller.dart`(`completeWithdrawal()`), `app/lib/core/router/app_router.dart`, `app/lib/l10n/app_strings.dart`, `app/test/support/fake_session_gateway.dart`, `app/test/features/auth/session_controller_test.dart`
- Delete: `app/lib/core/router/placeholder_screens.dart`
- Test: `app/test/features/account/state/withdraw_controller_test.dart`, `app/test/features/account/screens/withdraw_screen_test.dart`

**Interfaces:**
- Consumes: `AccountApi.withdraw`(Task 12), `sessionControllerProvider`, `socialSignInsProvider`
- Produces: `SessionGateway.clearLocal()`, `SessionController.completeWithdrawal()`, `WithdrawScreen`(`/settings/account/withdraw`)

동작 규칙 (점검표 S7·S12)
- 화면은 결과를 설명한다: 되돌릴 수 없다 / 매장의 기록은 매장에 남는다 / 소속과 내가 만든 초대 코드는 사라진다 / 같은 소셜 계정으로 다시 가입하면 새 계정이다. "안내를 확인했습니다"를 체크해야 "탈퇴하기"가 켜진다.
- 첫 요청은 **본문 없이** 보낸다. `SHOP_CLOSE_CONFIRM_REQUIRED`(409)면 "혼자 운영하는 매장도 함께 닫힙니다" 확인 시트 → 확인하면 본문 `{"confirm_close_shops": true}` 로 다시 보낸다. **값은 Dart `bool` 이다 — 서버는 StrictBool 이라 문자열 `"true"` 는 422 다.** 테스트가 실제로 나간 본문 바이트를 풀어 JSON 불리언인지, `content-type: application/json` 인지 확인한다.
- `OWNERSHIP_TRANSFER_REQUIRED`(409)면 문구와 "멤버 관리로 이동"(→ `/settings/members`)을 보여 준다. 다시 보내지 않는다.
- **204 와 401 을 둘 다 "탈퇴 완료"로 본다.** 같은 유저의 두 번째 탈퇴는 잠금에서 기다린 경우 204, 첫 탈퇴가 커밋된 뒤면 401 이다. 판정은 오류 `code` 가 아니라 `statusCode == 401` 로 한다 — 401 은 `ApiClient` 의 갱신을 거치면서 어떤 `code` 로 올라올지 보장되지 않는다.
- 완료 처리는 `completeWithdrawal()`: 토큰과 기기 설정을 **기기에서만** 지우고(`clearLocal()` — 서버 로그아웃을 부르지 않는다. 계정이 이미 없다) 상태를 `SignedOut()` 으로 둔다. `sessionExpired` 가 아니다 — 401 경로에서는 `ApiClient` 가 먼저 `endSession()` 을 불러 "보안을 위해 다시 로그인" 띠가 뜰 뻔하므로 덮어쓴다.
- 구글이 연결되어 있었으면 완료 뒤 `disconnect()` 를 한 번 부른다(실패는 삼킨다).
- 알고 두는 모호함: 액세스 토큰이 만료된 채 탈퇴를 눌렀는데 갱신까지 401 이면(다른 기기에서 세션이 폐기된 경우) 앱은 "완료"로 보지만 계정은 남아 있다. 다시 로그인하면 계정이 그대로 보인다. 서버가 204·401 을 같은 뜻으로 정했기 때문이고, 결정 기록 004 의 "남는 것"에 적는다(Task 17).

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`app/test/features/account/screens/withdraw_screen_test.dart`:
```dart
// 탈퇴 화면을 실제 라우터 + 가짜 HTTP 어댑터로 검증한다. AccountApi/
// WithdrawController/SessionController는 모두 진짜를 쓰고, 세션 게이트웨이만
// FakeSessionGateway로 문다.
import 'dart:convert';
import 'dart:typed_data';

import 'package:chagocnote/core/proxy/api_client.dart';
import 'package:chagocnote/core/proxy/providers.dart';
import 'package:chagocnote/core/router/app_router.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/core/storage/token_store.dart';
import 'package:chagocnote/design/app_theme.dart';
import 'package:chagocnote/design/bridge/glass_surface.dart';
import 'package:chagocnote/design/widgets/app_button.dart';
import 'package:chagocnote/features/auth/state/session.dart';
import 'package:chagocnote/features/auth/state/session_controller.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/fake_http_client_adapter.dart';
import '../../../support/fake_session_gateway.dart';

Me _me(List<String> identities) => Me(
      id: 1,
      displayName: '민석',
      profileImageUrl: null,
      identities: identities,
      shops: const [],
    );

final Finder _submitButton = find.byWidgetPredicate(
  (widget) => widget is AppButton && widget.label == AppStrings.withdrawSubmit,
);

({ProviderContainer container, FakeHttpClientAdapter adapter}) _setUp(
  FakeSessionGateway gateway,
  FakeHandler handle,
) {
  final adapter = FakeHttpClientAdapter(handle);
  final dio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final refreshDio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final tokenStore = _NoopTokenStore();
  final container = ProviderContainer.test(
    retry: (retryCount, error) => null,
    overrides: [
      sessionGatewayProvider.overrideWithValue(gateway),
      tokenStoreProvider.overrideWithValue(tokenStore),
      apiClientProvider.overrideWith(
        (ref) => ApiClient(
          tokenStore: tokenStore,
          dio: dio,
          refreshDio: refreshDio,
          onSessionEnded: ref.read(sessionEndedSignalProvider).fire,
        ),
      ),
    ],
  );
  return (container: container, adapter: adapter);
}

Widget _appWith(ProviderContainer container) {
  return UncontrolledProviderScope(
    container: container,
    child: Consumer(
      builder: (context, ref, _) {
        final router = ref.watch(routerProvider);
        return MaterialApp.router(
          routerConfig: router,
          theme: appTheme(),
          builder: (context, child) => GlassBridge(
            factory: const OpaqueSurfaceFactory(),
            child: child!,
          ),
        );
      },
    ),
  );
}

Future<void> _openWithdrawScreen(WidgetTester tester, ProviderContainer container) async {
  await tester.pumpWidget(_appWith(container));
  await tester.pumpAndSettle();
  container.read(routerProvider).go('/settings/account/withdraw');
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('체크박스를 누르기 전에는 탈퇴하기 버튼이 비활성화된다', (tester) async {
    final gateway = FakeSessionGateway()..meOnRestore = _me(['apple']);
    final setup = _setUp(gateway, (options, body) => fail('예상하지 못한 요청: ${options.path}'));
    addTearDown(setup.container.dispose);

    await _openWithdrawScreen(tester, setup.container);

    final button = tester.widget<AppButton>(_submitButton);
    expect(button.onPressed, isNull);

    await tester.tap(find.text(AppStrings.withdrawConfirmCheckbox));
    await tester.pumpAndSettle();

    final enabledButton = tester.widget<AppButton>(_submitButton);
    expect(enabledButton.onPressed, isNotNull);
  });

  testWidgets('204 는 탈퇴 완료로 처리하고 로그인 화면으로 간다(첫 요청은 본문이 없다)', (tester) async {
    final gateway = FakeSessionGateway()..meOnRestore = _me(['apple']);
    Uint8List? sentBody;
    final setup = _setUp(gateway, (options, body) {
      expect(options.method, 'DELETE');
      expect(options.path, '/v1/auth/account');
      sentBody = body;
      return const FakeResponse(statusCode: 204);
    });
    addTearDown(setup.container.dispose);

    await _openWithdrawScreen(tester, setup.container);
    await tester.tap(find.text(AppStrings.withdrawConfirmCheckbox));
    await tester.pumpAndSettle();
    await tester.tap(_submitButton);
    await tester.pumpAndSettle();

    expect(sentBody, isNull);
    expect(find.byKey(ScreenKeys.login), findsOneWidget);
    expect(gateway.clearLocalCalled, isTrue);
    expect(setup.adapter.requests.where((r) => r.path == '/v1/auth/logout'), isEmpty);
  });

  testWidgets('401 도 탈퇴 완료로 처리하고, endSession 이 먼저 불려도 만료 배너 없이 로그인 화면으로 간다(S12)', (
    tester,
  ) async {
    final gateway = FakeSessionGateway()..meOnRestore = _me(['apple']);
    final setup = _setUp(
      gateway,
      (options, body) => const FakeResponse(
        statusCode: 401,
        data: {'code': 'UNAUTHENTICATED', 'message': '이미 탈퇴됨'},
      ),
    );
    addTearDown(setup.container.dispose);

    await _openWithdrawScreen(tester, setup.container);
    await tester.tap(find.text(AppStrings.withdrawConfirmCheckbox));
    await tester.pumpAndSettle();
    await tester.tap(_submitButton);
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.login), findsOneWidget);
    expect(find.text(AppStrings.sessionExpiredBanner), findsNothing);
    expect(setup.adapter.requests.where((r) => r.path == '/v1/auth/logout'), isEmpty);
  });

  testWidgets('SHOP_CLOSE_CONFIRM_REQUIRED 를 확정하면 confirm_close_shops:true 인 두 번째 요청을 보낸다(S7)', (
    tester,
  ) async {
    final gateway = FakeSessionGateway()..meOnRestore = _me(['apple']);
    var callCount = 0;
    final setup = _setUp(gateway, (options, body) {
      callCount++;
      if (callCount == 1) {
        expect(body, isNull);
        return const FakeResponse(
          statusCode: 409,
          data: {'code': 'SHOP_CLOSE_CONFIRM_REQUIRED', 'message': '확인 필요'},
        );
      }
      expect(jsonDecode(utf8.decode(body!)), {'confirm_close_shops': true});
      expect(options.headers['content-type'], contains('application/json'));
      return const FakeResponse(statusCode: 204);
    });
    addTearDown(setup.container.dispose);

    await _openWithdrawScreen(tester, setup.container);
    await tester.tap(find.text(AppStrings.withdrawConfirmCheckbox));
    await tester.pumpAndSettle();
    await tester.tap(_submitButton);
    await tester.pumpAndSettle();

    expect(find.text(AppStrings.withdrawShopCloseTitle), findsOneWidget);
    await tester.tap(find.text(AppStrings.withdrawShopCloseConfirm));
    await tester.pumpAndSettle();

    expect(callCount, 2);
    expect(find.byKey(ScreenKeys.login), findsOneWidget);
  });

  testWidgets('매장 함께 닫기 시트를 취소하면 두 번째 요청을 보내지 않는다', (tester) async {
    final gateway = FakeSessionGateway()..meOnRestore = _me(['apple']);
    var callCount = 0;
    final setup = _setUp(gateway, (options, body) {
      callCount++;
      if (callCount > 1) fail('취소했는데 두 번째 요청이 나갔다');
      return const FakeResponse(
        statusCode: 409,
        data: {'code': 'SHOP_CLOSE_CONFIRM_REQUIRED', 'message': '확인 필요'},
      );
    });
    addTearDown(setup.container.dispose);

    await _openWithdrawScreen(tester, setup.container);
    await tester.tap(find.text(AppStrings.withdrawConfirmCheckbox));
    await tester.pumpAndSettle();
    await tester.tap(_submitButton);
    await tester.pumpAndSettle();

    await tester.tap(find.text(AppStrings.cancel));
    await tester.pumpAndSettle();

    expect(callCount, 1);
    expect(find.byKey(ScreenKeys.settingsAccountWithdraw), findsOneWidget);
  });

  testWidgets('OWNERSHIP_TRANSFER_REQUIRED 면 안내와 멤버 관리 버튼만 보여주고 재시도하지 않는다', (
    tester,
  ) async {
    final gateway = FakeSessionGateway()..meOnRestore = _me(['apple']);
    final setup = _setUp(
      gateway,
      (options, body) => const FakeResponse(
        statusCode: 409,
        data: {'code': 'OWNERSHIP_TRANSFER_REQUIRED', 'message': '소유권 이전 필요'},
      ),
    );
    addTearDown(setup.container.dispose);

    await _openWithdrawScreen(tester, setup.container);
    await tester.tap(find.text(AppStrings.withdrawConfirmCheckbox));
    await tester.pumpAndSettle();
    await tester.tap(_submitButton);
    await tester.pumpAndSettle();

    expect(find.text('혼자 사장인 매장에 다른 멤버가 있습니다. 먼저 다른 사장을 지정해 주세요.'), findsOneWidget);
    expect(find.text(AppStrings.goToMembers), findsOneWidget);
    expect(setup.adapter.requests, hasLength(1));
  });
}

class _NoopTokenStore implements TokenStore {
  @override
  Future<void> clear() async {}

  @override
  Future<String?> readAccess() async => null;

  @override
  Future<String?> readRefresh() async => null;

  @override
  Future<void> save({required String access, required String refresh}) async {}
}
```

`app/test/features/account/state/withdraw_controller_test.dart`:
```dart
// WithdrawController를 위젯 트리 없이 ProviderContainer로 직접 검증한다.
// 구글 연결 해제(베스트 에포트)처럼 화면 없이도 확인할 수 있는 동작에
// 집중한다 — 화면 흐름(시트, 오류 문구)은 withdraw_screen_test.dart에서 본다.
import 'package:chagocnote/core/proxy/api_client.dart';
import 'package:chagocnote/core/proxy/providers.dart';
import 'package:chagocnote/core/storage/token_store.dart';
import 'package:chagocnote/features/account/state/withdraw_controller.dart';
import 'package:chagocnote/features/auth/state/session.dart';
import 'package:chagocnote/features/auth/state/session_controller.dart';
import 'package:chagocnote/features/auth/state/social_sign_ins.dart';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/fake_http_client_adapter.dart';
import '../../../support/fake_session_gateway.dart';
import '../../../support/fake_social_sign_in.dart';

Me _me(List<String> identities) => Me(
      id: 1,
      displayName: '민석',
      profileImageUrl: null,
      identities: identities,
      shops: const [],
    );

({ProviderContainer container, FakeHttpClientAdapter adapter}) _setUp({
  required FakeSessionGateway gateway,
  required FakeHandler handle,
  List<FakeSocialSignIn> signIns = const [],
}) {
  final adapter = FakeHttpClientAdapter(handle);
  final dio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final refreshDio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final tokenStore = MemoryTokenStore();
  final container = ProviderContainer.test(
    retry: (retryCount, error) => null,
    overrides: [
      sessionGatewayProvider.overrideWithValue(gateway),
      socialSignInsProvider.overrideWithValue(signIns),
      tokenStoreProvider.overrideWithValue(tokenStore),
      apiClientProvider.overrideWith(
        (ref) => ApiClient(
          tokenStore: tokenStore,
          dio: dio,
          refreshDio: refreshDio,
          onSessionEnded: ref.read(sessionEndedSignalProvider).fire,
        ),
      ),
    ],
  );
  return (container: container, adapter: adapter);
}

void main() {
  test('구글이 연결되어 있었으면 탈퇴 후 disconnect() 를 한 번 부른다', () async {
    final gateway = FakeSessionGateway()..meOnRestore = _me(['apple', 'google']);
    final google = FakeSocialSignIn('google');
    final setup = _setUp(
      gateway: gateway,
      signIns: [google],
      handle: (options, body) => const FakeResponse(statusCode: 204),
    );
    addTearDown(setup.container.dispose);
    await setup.container.read(sessionControllerProvider.future);

    await setup.container.read(withdrawControllerProvider.notifier).withdraw();

    expect(google.disconnectCallCount, 1);
    expect(gateway.clearLocalCalled, isTrue);
  });

  test('구글이 없었으면 disconnect() 를 부르지 않는다', () async {
    final gateway = FakeSessionGateway()..meOnRestore = _me(['apple']);
    final google = FakeSocialSignIn('google');
    final setup = _setUp(
      gateway: gateway,
      signIns: [google],
      handle: (options, body) => const FakeResponse(statusCode: 204),
    );
    addTearDown(setup.container.dispose);
    await setup.container.read(sessionControllerProvider.future);

    await setup.container.read(withdrawControllerProvider.notifier).withdraw();

    expect(google.disconnectCallCount, 0);
  });

  test('disconnect() 가 던져도 탈퇴 자체는 실패하지 않는다', () async {
    final gateway = FakeSessionGateway()..meOnRestore = _me(['apple', 'google']);
    final google = FakeSocialSignIn('google')..disconnectError = Exception('실패');
    final setup = _setUp(
      gateway: gateway,
      signIns: [google],
      handle: (options, body) => const FakeResponse(statusCode: 204),
    );
    addTearDown(setup.container.dispose);
    await setup.container.read(sessionControllerProvider.future);

    await setup.container.read(withdrawControllerProvider.notifier).withdraw();

    expect(google.disconnectCallCount, 1);
    expect(gateway.clearLocalCalled, isTrue);
  });
}
```

`app/test/features/auth/session_controller_test.dart` — 바꾼다:
```diff
--- a/test/features/auth/session_controller_test.dart
+++ b/test/features/auth/session_controller_test.dart
@@ -210,6 +210,39 @@ void main() {
     });
   });
 
+  group('completeWithdrawal', () {
+    test('로컬을 지우고 sessionExpired 가 아닌 SignedOut 으로 만든다', () async {
+      final gateway = FakeSessionGateway()..meOnRestore = _me(shops: [_ownerA]);
+      final container = _containerWith(gateway);
+      await container.read(sessionControllerProvider.future);
+
+      final notifier = container.read(sessionControllerProvider.notifier);
+      await notifier.completeWithdrawal();
+
+      expect(gateway.clearLocalCalled, isTrue);
+      final state = container.read(sessionControllerProvider).value as SignedOut;
+      expect(state.sessionExpired, isFalse);
+    });
+
+    test('endSession 이 먼저 불렸어도 sessionExpired 를 되돌린다(401 경로)', () async {
+      final gateway = FakeSessionGateway()..meOnRestore = _me(shops: [_ownerA]);
+      final container = _containerWith(gateway);
+      await container.read(sessionControllerProvider.future);
+
+      final notifier = container.read(sessionControllerProvider.notifier);
+      notifier.endSession();
+      expect(
+        (container.read(sessionControllerProvider).value as SignedOut).sessionExpired,
+        isTrue,
+      );
+
+      await notifier.completeWithdrawal();
+
+      final state = container.read(sessionControllerProvider).value as SignedOut;
+      expect(state.sessionExpired, isFalse);
+    });
+  });
+
   test('endSession 은 즉시 sessionExpired 가 true 인 SignedOut 으로 만든다', () async {
     final gateway = FakeSessionGateway()..meOnRestore = _me(shops: [_ownerA]);
     final container = _containerWith(gateway);
```

`app/test/support/fake_session_gateway.dart` — 바꾼다:
```diff
--- a/test/support/fake_session_gateway.dart
+++ b/test/support/fake_session_gateway.dart
@@ -27,6 +27,8 @@ class FakeSessionGateway implements SessionGateway {
   bool signOutCalled = false;
   int? writtenShopId;
 
+  bool clearLocalCalled = false;
+
   @override
   Future<Me?> restore() async {
     restoreCallCount++;
@@ -61,4 +63,9 @@ class FakeSessionGateway implements SessionGateway {
     writtenShopId = shopId;
     lastShopId = shopId;
   }
+
+  @override
+  Future<void> clearLocal() async {
+    clearLocalCalled = true;
+  }
 }
```

Run: `flutter test test/features/account test/features/auth/session_controller_test.dart`
Expected: FAIL

- [ ] **Step 2: 구현한다**

`app/lib/core/router/app_router.dart` — 바꾼다:
```diff
--- a/lib/core/router/app_router.dart
+++ b/lib/core/router/app_router.dart
@@ -3,6 +3,7 @@ import 'package:flutter_riverpod/flutter_riverpod.dart';
 import 'package:go_router/go_router.dart';
 
 import '../../features/account/screens/account_screen.dart';
+import '../../features/account/screens/withdraw_screen.dart';
 import '../../features/auth/screens/invite_code_screen.dart';
 import '../../features/auth/screens/login_screen.dart';
 import '../../features/auth/screens/shop_select_screen.dart';
@@ -13,7 +14,6 @@ import '../../features/home/screens/home_shell.dart';
 import '../../features/shop/screens/members_screen.dart';
 import '../../features/shop/screens/settings_screen.dart';
 import '../../features/shop/screens/shop_settings_screen.dart';
-import 'placeholder_screens.dart';
 
 /// go_router의 `refreshListenable`은 평범한 [Listenable]을 요구한다. 세션이
 /// 바뀔 때마다 이걸로 "redirect를 다시 평가해라"라고 알린다.
@@ -92,7 +92,7 @@ final routerProvider = Provider<GoRouter>((ref) {
       ),
       GoRoute(
         path: '/settings/account/withdraw',
-        builder: (context, state) => const SettingsAccountWithdrawScreen(),
+        builder: (context, state) => const WithdrawScreen(),
       ),
     ],
   );
```

`app/lib/core/router/placeholder_screens.dart` — 지운다(자리 표시 화면이 전부 진짜 화면으로 바뀌었다). `git rm app/lib/core/router/placeholder_screens.dart`

`app/lib/features/account/screens/withdraw_screen.dart`:
```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/error/api_exception.dart';
import '../../../core/error/error_messages.dart';
import '../../../core/router/screen_keys.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_button.dart';
import '../../../design/widgets/app_sheet.dart';
import '../../../l10n/app_strings.dart';
import '../state/withdraw_controller.dart';

/// 회원 탈퇴 화면. 안내를 확인해야 탈퇴 버튼이 활성화되고, 서버가 추가
/// 확인을 요구하면(매장 함께 닫기) 시트로 물어본 뒤 다시 요청한다.
class WithdrawScreen extends ConsumerStatefulWidget {
  const WithdrawScreen({super.key});

  @override
  ConsumerState<WithdrawScreen> createState() => _WithdrawScreenState();
}

class _WithdrawScreenState extends ConsumerState<WithdrawScreen> {
  bool _agreed = false;
  bool _busy = false;
  String? _errorText;
  bool _ownershipTransferRequired = false;

  Future<void> _withdraw({bool confirmCloseShops = false}) async {
    setState(() {
      _busy = true;
      _errorText = null;
      _ownershipTransferRequired = false;
    });
    try {
      await ref
          .read(withdrawControllerProvider.notifier)
          .withdraw(confirmCloseShops: confirmCloseShops);
      // 성공하면 세션이 로그아웃 상태가 되고 라우터가 로그인 화면으로
      // 보낸다. 화면이 아직 남아 있다면(드문 경우) busy만 풀어 둔다.
      if (mounted) setState(() => _busy = false);
    } on ApiException catch (e) {
      if (!mounted) return;
      if (e.code == 'SHOP_CLOSE_CONFIRM_REQUIRED') {
        setState(() => _busy = false);
        final confirmed = await _confirmShopClose();
        if (confirmed == true && mounted) {
          await _withdraw(confirmCloseShops: true);
        }
        return;
      }
      setState(() {
        _busy = false;
        _errorText = messageFor(e);
        _ownershipTransferRequired = e.code == 'OWNERSHIP_TRANSFER_REQUIRED';
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _busy = false;
        _errorText = messageFor(e);
      });
    }
  }

  Future<bool?> _confirmShopClose() {
    return AppSheet.show<bool>(
      context,
      builder: (context) => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            AppStrings.withdrawShopCloseTitle,
            style: AppTypography.body,
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: AppSpacing.lg),
          AppButton(
            label: AppStrings.withdrawShopCloseConfirm,
            filled: true,
            onPressed: () => Navigator.of(context).pop(true),
          ),
          const SizedBox(height: AppSpacing.sm),
          AppButton(
            label: AppStrings.cancel,
            onPressed: () => Navigator.of(context).pop(false),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      key: ScreenKeys.settingsAccountWithdraw,
      body: AppBackground(
        child: SafeArea(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(AppSpacing.lg),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(AppStrings.withdraw, style: AppTypography.titleKo),
                const SizedBox(height: AppSpacing.xl),
                _NoticeLine(AppStrings.withdrawNoticeIrreversible),
                _NoticeLine(AppStrings.withdrawNoticeShopRecordsStay),
                _NoticeLine(AppStrings.withdrawNoticeMembershipGone),
                _NoticeLine(AppStrings.withdrawNoticeNewAccount),
                const SizedBox(height: AppSpacing.xl),
                CheckboxListTile(
                  value: _agreed,
                  onChanged: _busy
                      ? null
                      : (checked) => setState(() => _agreed = checked ?? false),
                  controlAffinity: ListTileControlAffinity.leading,
                  contentPadding: EdgeInsets.zero,
                  title: Text(
                    AppStrings.withdrawConfirmCheckbox,
                    style: AppTypography.body,
                  ),
                ),
                const SizedBox(height: AppSpacing.lg),
                AppButton(
                  label: AppStrings.withdrawSubmit,
                  filled: true,
                  busy: _busy,
                  onPressed: (_agreed && !_busy) ? () => _withdraw() : null,
                ),
                if (_errorText != null) ...[
                  const SizedBox(height: AppSpacing.lg),
                  Text(_errorText!, style: AppTypography.caption),
                ],
                if (_ownershipTransferRequired) ...[
                  const SizedBox(height: AppSpacing.sm),
                  AppButton(
                    label: AppStrings.goToMembers,
                    onPressed: () => context.push('/settings/members'),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _NoticeLine extends StatelessWidget {
  const _NoticeLine(this.text);

  final String text;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: AppSpacing.sm),
        child: Text('· $text', style: AppTypography.body),
      );
}
```

`app/lib/features/account/state/withdraw_controller.dart`:
```dart
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../auth/state/session_controller.dart';
import '../../auth/state/social_sign_ins.dart';
import 'account_controller.dart';

/// 탈퇴 화면의 동작을 담당한다. `AccountApi.withdraw`가 204/401을 모두
/// 성공으로 취급하므로, 이 메서드가 던지지 않고 끝나면 곧 탈퇴가 끝난
/// 것이다 — 세션을 로컬에서만 정리한다. 서버가 추가 확인을 요구하면
/// (매장 함께 닫기 등) 화면이 오류 코드를 보고 [confirmCloseShops]를 담아
/// 다시 부른다.
class WithdrawController extends Notifier<AsyncValue<void>> {
  SessionController get _session =>
      ref.read(sessionControllerProvider.notifier);

  @override
  AsyncValue<void> build() => const AsyncData(null);

  Future<void> withdraw({bool confirmCloseShops = false}) async {
    // 세션이 사라지기 전에 로그인 수단을 먼저 읽어 둔다 — 구글이 있었다면
    // 탈퇴 뒤에도 SDK 연결을 끊어야 하는데, 그때는 이미 로그아웃 상태라
    // `Me.identities`를 더 읽을 수 없다.
    final identities = ref.read(accountIdentitiesProvider);
    await ref
        .read(accountApiProvider)
        .withdraw(confirmCloseShops: confirmCloseShops);
    await _session.completeWithdrawal();
    if (identities.contains('google')) {
      await _disconnectGoogle();
    }
  }

  Future<void> _disconnectGoogle() async {
    for (final signIn in ref.read(socialSignInsProvider)) {
      if (signIn.provider != 'google') continue;
      try {
        await signIn.disconnect();
      } catch (_) {
        // 베스트 에포트 — 탈퇴 자체는 이미 끝났다.
      }
      return;
    }
  }
}

final withdrawControllerProvider =
    NotifierProvider<WithdrawController, AsyncValue<void>>(
  WithdrawController.new,
);
```

`app/lib/features/auth/state/session_controller.dart` — 바꾼다:
```diff
--- a/lib/features/auth/state/session_controller.dart
+++ b/lib/features/auth/state/session_controller.dart
@@ -97,6 +97,16 @@ class SessionController extends AsyncNotifier<Session> {
     state = const AsyncData(SignedOut(sessionExpired: true));
   }
 
+  /// 회원 탈퇴 완료 처리. 계정이 이미 사라졌으므로 서버에 통보하지 않고
+  /// 로컬 토큰·설정만 지운다. `sessionExpired`는 세우지 않는다 — 탈퇴
+  /// 직후에 "보안을 위해 다시 로그인해 주세요" 배너를 보여주는 건 맞지
+  /// 않다(401 경로에서는 이미 `endSession()`이 먼저 불렸을 수 있어서, 이
+  /// 메서드가 그 상태를 덮어써야 한다).
+  Future<void> completeWithdrawal() async {
+    await _gateway.clearLocal();
+    state = const AsyncData(SignedOut());
+  }
+
   /// 이미 가지고 있는 [Me]로 상태를 교체한다. `reloadMe`와 같은 선택 규칙을
   /// 쓰지만, 네트워크 호출이 없으므로 동기로 끝낼 수 있다: 현재 선택된
   /// 매장이 새 소속 목록에도 있으면 유지하고, 없으면 매장이 하나뿐일 때만
```

`app/lib/features/auth/state/session_gateway.dart` — 바꾼다:
```diff
--- a/lib/features/auth/state/session_gateway.dart
+++ b/lib/features/auth/state/session_gateway.dart
@@ -16,6 +16,10 @@ abstract class SessionGateway {
   Future<Me> refreshMe();
   Future<int?> readLastShopId();
   Future<void> writeLastShopId(int shopId);
+
+  /// 로컬 토큰·설정만 지운다. 서버에 통보하지 않는다 — 회원 탈퇴처럼 계정이
+  /// 이미 사라져서 알릴 서버가 없는 경우에 쓴다.
+  Future<void> clearLocal();
 }
 
 /// [AuthApi]·[MeApi]·[TokenStore]·[PrefsStore]로 만든 실제 구현.
@@ -83,4 +87,10 @@ class HttpSessionGateway implements SessionGateway {
   @override
   Future<void> writeLastShopId(int shopId) =>
       _prefsStore.writeLastShopId(shopId);
+
+  @override
+  Future<void> clearLocal() async {
+    await _tokenStore.clear();
+    await _prefsStore.clear();
+  }
 }
```

`app/lib/l10n/app_strings.dart` — 바꾼다:
```diff
--- a/lib/l10n/app_strings.dart
+++ b/lib/l10n/app_strings.dart
@@ -78,4 +78,15 @@ class AppStrings {
   static const unlinkOnlyOneCaption = '마지막 로그인 수단은 해제할 수 없습니다.';
   static const unlinkConfirmMessage = '해제하면 다른 모든 기기에서 로그아웃됩니다.';
   static const withdraw = '회원 탈퇴';
+
+  // 회원 탈퇴
+  static const withdrawNoticeIrreversible = '되돌릴 수 없습니다.';
+  static const withdrawNoticeShopRecordsStay = '매장의 기록은 매장에 남습니다.';
+  static const withdrawNoticeMembershipGone = '소속과 초대 코드는 사라집니다.';
+  static const withdrawNoticeNewAccount = '같은 소셜 계정으로 다시 가입하면 새 계정이 됩니다.';
+  static const withdrawConfirmCheckbox = '안내를 확인했습니다';
+  static const withdrawSubmit = '탈퇴하기';
+  static const withdrawShopCloseTitle = '혼자 운영하는 매장도 함께 닫힙니다';
+  static const withdrawShopCloseConfirm = '매장을 닫고 탈퇴';
+  static const goToMembers = '멤버 관리로 이동';
 }
```

- [ ] **Step 3: 통과를 확인하고 커밋한다**

Run: `flutter test && flutter analyze`
Expected: `All tests passed!` (새 테스트 파일 기준 9개 + 세션 컨트롤러 테스트에 더한 것), `No issues found!`

```bash
git add -A app/lib app/test
git commit -m "feat(app): 회원 탈퇴 — 확인값은 JSON 불리언, 204 와 401 은 둘 다 완료"
```

### Task 14: 카카오·구글·Apple 로그인 구현 (Dart 쪽) 과 네이티브 설정 안내

**Files:**
- Modify: `app/pubspec.yaml` (`crypto` 추가)
- Create: `app/lib/features/auth/api/kakao_sign_in.dart`, `google_sign_in_adapter.dart`, `apple_sign_in.dart`, `apple_nonce.dart`
- Modify: `app/lib/features/auth/state/social_sign_ins.dart`, `app/lib/main.dart`
- Create: `app/NATIVE-SETUP.md`
- Test: `app/test/features/auth/api/apple_nonce_test.dart`, `app/test/features/auth/state/social_sign_ins_test.dart`

**Interfaces:**
- Consumes: `SocialSignIn`·`SocialCredential`(Task 6), `AppConfig`(Task 1), Task 1 에서 설치한 `kakao_flutter_sdk_user`·`google_sign_in`·`sign_in_with_apple`
- Produces: `KakaoSignIn`, `GoogleSignInAdapter`, `AppleSignIn`(모두 `SocialSignIn`), `newRawNonce()`·`hashNonce(String)`, 설정에 따라 채워지는 `socialSignInsProvider`

범위 — **카카오·구글·Apple 의 키가 아직 없다**(설계 8.3: 등록은 사용자만 할 수 있고, Apple 은 유료 개발자 가입이 필요하다). 그래서 이 작업은 Dart 쪽 구현과 "키가 생기면 할 네이티브 설정" 문서까지다. `Info.plist` 의 URL 스킴이나 Apple 로그인 권한은 실제 키 없이는 확인할 수 없으므로 **지금 프로젝트에 넣지 않는다.** 그 전까지 앱은 `APP_ENV=dev` 의 개발용 로그인으로 돈다.

규칙
- **웹뷰를 쓰지 않는다.** 카카오는 카카오톡 앱 전환(`loginWithKakaoTalk`)을 먼저 시도하고, 카카오톡이 없을 때만 `loginWithKakaoAccount`(SDK 가 여는 시스템 인증 세션)로 간다. 구글은 네이티브 SDK 다. **Apple 은 iOS 에서만 제공한다**(Android 의 Apple 로그인은 웹 흐름뿐이다).
- 취소는 `null` 이다. SDK 마다 취소 신호가 다르다(패키지 소스로 확인): 카카오톡 앱 전환의 취소는 `PlatformException(code: 'CANCELED')`, 카카오계정 동의 화면의 취소는 `KakaoAuthException(error: AuthErrorCause.accessDenied)`, 구글은 `GoogleSignInException` 의 취소 코드, Apple 은 `AuthorizationErrorCode.canceled`.
- Apple nonce: **Apple 에는 `sha256(원본)` 의 16진 문자열을, 서버에는 원본을 보낸다.** 백엔드가 `sha256(nonce).hexdigest() == idToken.nonce` 로 확인한다(`apple_identity_strategy.py`). 거꾸로 하면 검증이 실패한다. SHA-256 때문에 `crypto`(dart-lang 공식)를 더한다 — 설계 6.1 의 9개 목록에서 벗어나는 유일한 추가다(결정 기록 004 에 적는다).
- 구글 서버 쪽 연결 끊기는 없다. `disconnect()` 는 `GoogleSignIn.instance.disconnect()` 다. 카카오의 `disconnect()` 는 아무것도 하지 않는다(서버가 어드민 키로 끊는다).
- SDK 어댑터는 플랫폼 채널 없이 단위 테스트할 수 없다. **SDK 를 가짜로 흉내 내는 테스트를 쓰지 않는다.** 테스트하는 것은 nonce 도우미와 `socialSignInsProvider` 의 조립(설정·플랫폼별)뿐이다.

- [ ] **Step 1: `crypto` 를 더한다**

Run (`app/` 에서): `flutter pub add crypto`
`retracted` 경고와 함께 컴파일이 깨지면 Task 1 의 사실대로 `pubspec.lock` 을 지우고 `flutter pub get` 을 다시 한다.

- [ ] **Step 2: 실패하는 테스트를 쓴다**

`app/test/features/auth/api/apple_nonce_test.dart`:
```dart
// 순수 Dart 헬퍼라 SDK/플랫폼 채널 없이 바로 검증한다.
import 'package:chagocnote/features/auth/api/apple_nonce.dart';
import 'package:flutter_test/flutter_test.dart';

final _base64UrlSafe = RegExp(r'^[A-Za-z0-9_-]+$');

void main() {
  group('hashNonce', () {
    test('알려진 입력의 SHA-256 16진수 해시와 일치한다', () {
      expect(
        hashNonce('abc'),
        'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad',
      );
    });
  });

  group('newRawNonce', () {
    test('두 번 호출한 값은 서로 다르다', () {
      expect(newRawNonce(), isNot(newRawNonce()));
    });

    test('URL-safe 문자만 쓰고 패딩(=)이 없다', () {
      final raw = newRawNonce();
      expect(_base64UrlSafe.hasMatch(raw), isTrue);
      expect(raw.contains('='), isFalse);
    });

    test('32바이트를 base64url로 인코딩한 길이다(패딩 제외 43자)', () {
      expect(newRawNonce().length, 43);
    });
  });
}
```

`app/test/features/auth/state/social_sign_ins_test.dart`:
```dart
// 실제 SDK 어댑터는 플랫폼 채널 없이는 단위 테스트할 수 없다(브리핑 지시).
// 여기서는 `socialSignInsProvider`가 설정 조합·플랫폼에 따라 올바른
// provider 목록을 구성하는지만 검증한다.
import 'package:chagocnote/core/config/app_config.dart';
import 'package:chagocnote/core/proxy/providers.dart';
import 'package:chagocnote/features/auth/api/apple_sign_in.dart';
import 'package:chagocnote/features/auth/api/google_sign_in_adapter.dart';
import 'package:chagocnote/features/auth/api/kakao_sign_in.dart';
import 'package:chagocnote/features/auth/state/social_sign_ins.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

const _empty = AppConfig(apiBaseUrl: '', appEnv: 'dev');
const _kakaoOnly = AppConfig(
  apiBaseUrl: '',
  appEnv: 'dev',
  kakaoNativeAppKey: 'kakao-key',
);
const _googleOnly = AppConfig(
  apiBaseUrl: '',
  appEnv: 'dev',
  googleServerClientId: 'server-client-id',
);
const _appleOnly = AppConfig(
  apiBaseUrl: '',
  appEnv: 'dev',
  appleSignInEnabled: true,
);
const _all = AppConfig(
  apiBaseUrl: '',
  appEnv: 'dev',
  kakaoNativeAppKey: 'kakao-key',
  googleServerClientId: 'server-client-id',
  appleSignInEnabled: true,
);

List<String> _providersOf(ProviderContainer container) =>
    container.read(socialSignInsProvider).map((s) => s.provider).toList();

void main() {
  tearDown(() {
    debugDefaultTargetPlatformOverride = null;
  });

  test('빈 설정이면 목록이 비어 있다(개발용 로그인만 남는다)', () {
    final container = ProviderContainer.test(
      overrides: [appConfigProvider.overrideWithValue(_empty)],
    );
    addTearDown(container.dispose);

    expect(container.read(socialSignInsProvider), isEmpty);
  });

  test('kakaoEnabled 면 카카오 어댑터가 포함된다', () {
    final container = ProviderContainer.test(
      overrides: [appConfigProvider.overrideWithValue(_kakaoOnly)],
    );
    addTearDown(container.dispose);

    final signIns = container.read(socialSignInsProvider);
    expect(signIns, hasLength(1));
    expect(signIns.single, isA<KakaoSignIn>());
  });

  test('googleEnabled 면 구글 어댑터가 포함된다', () {
    final container = ProviderContainer.test(
      overrides: [appConfigProvider.overrideWithValue(_googleOnly)],
    );
    addTearDown(container.dispose);

    final signIns = container.read(socialSignInsProvider);
    expect(signIns, hasLength(1));
    expect(signIns.single, isA<GoogleSignInAdapter>());
  });

  test('appleSignInEnabled 여도 안드로이드에서는 제공하지 않는다', () {
    debugDefaultTargetPlatformOverride = TargetPlatform.android;
    final container = ProviderContainer.test(
      overrides: [appConfigProvider.overrideWithValue(_appleOnly)],
    );
    addTearDown(container.dispose);

    expect(container.read(socialSignInsProvider), isEmpty);
  });

  test('appleSignInEnabled 고 iOS 면 애플 어댑터가 포함된다', () {
    debugDefaultTargetPlatformOverride = TargetPlatform.iOS;
    final container = ProviderContainer.test(
      overrides: [appConfigProvider.overrideWithValue(_appleOnly)],
    );
    addTearDown(container.dispose);

    final signIns = container.read(socialSignInsProvider);
    expect(signIns, hasLength(1));
    expect(signIns.single, isA<AppleSignIn>());
  });

  test('전부 켜져 있고 iOS 면 카카오·구글·애플 순서로 셋 다 포함된다', () {
    debugDefaultTargetPlatformOverride = TargetPlatform.iOS;
    final container = ProviderContainer.test(
      overrides: [appConfigProvider.overrideWithValue(_all)],
    );
    addTearDown(container.dispose);

    expect(_providersOf(container), ['kakao', 'google', 'apple']);
  });
}
```

Run: `flutter test test/features/auth/api test/features/auth/state`
Expected: FAIL

- [ ] **Step 3: 구현한다**

`app/NATIVE-SETUP.md` (키가 생기면 할 일 — 지금은 적용하지 않는다):
````markdown
# 네이티브 설정 — 키가 생기면 할 일

**지금은 적용하지 않는다.** 카카오/구글/애플 어느 쪽도 아직 실제 앱/서비스
등록을 하지 않았고(애플은 유료 개발자 멤버십도 필요하다), 진짜 키 없이는
검증할 수 없다. 이 문서는 키가 생겼을 때 무엇을, 어느 파일에, 왜 넣어야
하는지를 패키지 캐시의 실제 소스로 근거를 남겨 둔 것이다.

각 항목은 `~/.pub-cache/hosted/pub.dev/<패키지>/<경로>`를 인용한다 —
버전은 `t14` 기준(kakao 2.0.1, google_sign_in 7.2.0/이오에스 6.3.5/안드로이드
7.2.17, sign_in_with_apple 8.2.0)이다.

## 공통 — `--dart-define`

`lib/core/config/app_config.dart`(`AppConfig.fromEnvironment`)가 읽는 이름
그대로다. 값이 비어 있으면(카카오/구글) 또는 `false`면(애플) 그 공급자는
`socialSignInsProvider` 목록에서 아예 빠진다.

| 이름 | 의미 |
|---|---|
| `KAKAO_NATIVE_APP_KEY` | 카카오 개발자 콘솔의 네이티브 앱 키 |
| `GOOGLE_IOS_CLIENT_ID` | iOS OAuth 클라이언트 ID (`GoogleService-Info.plist`의 `CLIENT_ID`) |
| `GOOGLE_SERVER_CLIENT_ID` | 백엔드가 id 토큰을 검증할 웹 OAuth 클라이언트 ID |
| `APPLE_SIGN_IN_ENABLED` | `true`/`false`. iOS에서만 실제로 버튼이 뜬다(안드로이드에서 애플은 웹 플로우라 이 브랜치에서 제공하지 않는다) |

예: `flutter run --dart-define=KAKAO_NATIVE_APP_KEY=xxxx --dart-define=GOOGLE_SERVER_CLIENT_ID=yyyy.apps.googleusercontent.com --dart-define=APPLE_SIGN_IN_ENABLED=true`

---

## 카카오 (`kakao_flutter_sdk_user` 2.0.1 / `kakao_flutter_sdk_common` 2.0.1)

패키지 자체 `README.md`(`~/.pub-cache/hosted/pub.dev/kakao_flutter_sdk_user-2.0.1/README.md`)는
설정 방법을 전부 외부 문서(developers.kakao.com)로만 링크해 두어서, 아래
항목은 README 대신 **플러그인의 실제 소스**를 근거로 삼았다(경로를 각각
적었다).

### iOS `Info.plist`

- `CFBundleURLTypes`에 `kakao{NATIVE_APP_KEY}` 스킴을 등록한다. 이 스킴은
  카카오계정 로그인의 콜백(redirect) 주소로 쓰인다 — 근거:
  `~/.pub-cache/hosted/pub.dev/kakao_flutter_sdk_common-2.0.1/lib/src/kakao_sdk.dart:68`
  (`_customScheme = customScheme ?? 'kakao$appKey';`)와 `:32`
  (`redirectUri => '$customScheme://oauth'`).
  ```xml
  <key>CFBundleURLTypes</key>
  <array>
    <dict>
      <key>CFBundleTypeRole</key>
      <string>Editor</string>
      <key>CFBundleURLSchemes</key>
      <array>
        <string>kakao{NATIVE_APP_KEY}</string>
      </array>
    </dict>
  </array>
  ```
- `LSApplicationQueriesSchemes`에 `kakaokompassauth`를 추가한다 — 카카오톡
  설치 여부를 `canOpenURL`로 확인할 때 쓰는 스킴이다. 근거:
  `~/.pub-cache/hosted/pub.dev/kakao_flutter_sdk_common-2.0.1/ios/kakao_flutter_sdk_common/Sources/kakao_flutter_sdk_common/CommonHostApiImpl.swift:23-27`
  (`isKakaoTalkAvailable`가 기본값 `"kakaokompassauth://authorize"`로
  `UIApplication.shared.canOpenURL`을 부른다). `LSApplicationQueriesSchemes`에
  없는 스킴은 iOS 9+에서 `canOpenURL`이 항상 false를 돌려주므로, `isKakaoTalkInstalled()`가
  카카오톡이 있어도 없다고 오판한다.
  ```xml
  <key>LSApplicationQueriesSchemes</key>
  <array>
    <string>kakaokompassauth</string>
  </array>
  ```
  - **참고(정확히 확인한 것)**: `kakaolink` 스킴은 인바운드 딥링크 처리에서만
    쓰인다 — `~/.pub-cache/hosted/pub.dev/kakao_flutter_sdk_common-2.0.1/ios/kakao_flutter_sdk_common/Sources/kakao_flutter_sdk_common/KakaoFlutterSdkCommonPlugin.swift:52-58`의
    `handleIncomingDeepLinks`가 들어오는 URL의 `host == "kakaolink"`인지만
    본다 — 이건 앱이 "받는" URL이라 `LSApplicationQueriesSchemes`(앱이
    "여는" URL을 미리 선언하는 목록)에 넣을 필요가 없다. 로그인 전용
    (`kakao_flutter_sdk_user`)인 이 브랜치에서는 `kakaokompassauth` 하나면
    충분하다 — 카카오톡 공유/메시지 기능까지 붙이면 그때 다시 확인한다.

### 카카오톡 앱 실행 후 되돌아오는 경로 (Android)

`AuthCodeHandlerActivity`가 플러그인 자체 매니페스트(`exported="true"`)에는
있지만 인텐트 필터가 없다 — 근거:
`~/.pub-cache/hosted/pub.dev/kakao_flutter_sdk_auth-2.0.1/android/src/main/AndroidManifest.xml`.
앱의 `android/app/src/main/AndroidManifest.xml`의 `<application>` 안에
같은 액티비티를 스킴 딸린 인텐트 필터로 다시 선언해서(매니페스트 병합)
`kakao{NATIVE_APP_KEY}` 스킴의 콜백을 받게 해야 한다:
```xml
<activity
    android:name="com.kakao.sdk.flutter.auth.AuthCodeHandlerActivity"
    android:exported="true">
  <intent-filter>
    <action android:name="android.intent.action.VIEW" />
    <category android:name="android.intent.category.DEFAULT" />
    <category android:name="android.intent.category.BROWSABLE" />
    <data android:scheme="kakao{NATIVE_APP_KEY}" android:host="oauth" />
  </intent-filter>
</activity>
```
(패키지 소스 자체에는 이 인텐트 필터 예시가 없다 — 카카오 개발자 문서의
표준 안내를 그대로 따른 것이니, 실제 키가 생기면 developers.kakao.com의
최신 안드로이드 가이드로 한 번 더 대조해야 한다.)

### `KakaoSdk.init`

`lib/main.dart`에 이미 `config.kakaoEnabled`로 감싼 초기화를 배선해
두었다(`KakaoSdk.init(nativeAppKey: config.kakaoNativeAppKey)`) — 근거:
`~/.pub-cache/hosted/pub.dev/kakao_flutter_sdk_common-2.0.1/lib/src/kakao_sdk.dart:50`
(`static Future<void> init({String? nativeAppKey, ...})`).

---

## 구글 (`google_sign_in` 7.2.0)

### iOS `Info.plist`

근거: `~/.pub-cache/hosted/pub.dev/google_sign_in_ios-6.3.5/README.md`
("iOS integration" 절, 그대로 인용).
```xml
<key>GIDClientID</key>
<string>{GOOGLE_IOS_CLIENT_ID}</string>

<!-- 백엔드 검증용 서버 클라이언트 ID -->
<key>GIDServerClientID</key>
<string>{GOOGLE_SERVER_CLIENT_ID}</string>

<key>CFBundleURLTypes</key>
<array>
  <dict>
    <key>CFBundleTypeRole</key>
    <string>Editor</string>
    <key>CFBundleURLSchemes</key>
    <array>
      <!-- GoogleService-Info.plist 의 REVERSED_CLIENT_ID -->
      <string>com.googleusercontent.apps.XXXXXXXXX-yyyyyyyy</string>
    </array>
  </dict>
</array>
```
`GIDClientID`/`GIDServerClientID`는 우리 앱처럼 `GoogleSignIn.instance.initialize(clientId:, serverClientId:)`를
Dart 코드에서 직접 넘기면 생략해도 된다고 README가 명시한다(단, `CFBundleURLTypes`의
`REVERSED_CLIENT_ID`는 Info.plist에 그대로 필요하다 — 이건 코드로 대체할
수 없는 URL 스킴 등록이다).

### Android

매니페스트에 넣을 항목은 없다(구글 로그인은 Credential Manager를 쓰지,
카카오처럼 커스텀 스킴 액티비티를 등록하지 않는다) — 대신 콘솔 등록이
필요하다. 근거: `~/.pub-cache/hosted/pub.dev/google_sign_in_android-7.2.17/README.md`.
- Firebase 또는 Google Cloud Platform 콘솔에 앱의 **서명 SHA-1**을 등록한다
  (디버그·릴리스 키스토어 각각).
- `google-services.json`을 쓰지 않는다면 `serverClientId`(웹 OAuth 클라이언트
  ID)를 `GoogleSignIn.instance.initialize`에 직접 넘겨야 한다 — 우리
  `GoogleSignInAdapter`는 이미 `AppConfig.googleServerClientId`를 그렇게
  넘기고 있다.
- **README가 짚어 둔 트러블슈팅 gotcha**: SHA-1이나 `serverClientId`가
  잘못 설정되면, 사용자가 계정을 고른 **뒤에** `GoogleSignInExceptionCode.canceled`가
  올라올 수 있다 — 우리 어댑터는 이 코드를 "취소"로 보고 `null`을
  돌려주므로, 실제로는 설정 오류인데 조용히 로그인 화면에 남아 있는
  것처럼 보일 수 있다. 실기기에서 처음 연결할 때 이 gotcha를 염두에 둔다.

---

## 애플 (`sign_in_with_apple` 8.2.0)

이 브랜치는 iOS에서만 애플 로그인을 제공한다(`social_sign_ins.dart`가
`defaultTargetPlatform == TargetPlatform.iOS`로 막아 둔다) — 그래서
안드로이드/웹 설정은 여기 적지 않는다.

### 전제조건

- **유료 Apple Developer Program 멤버십이 필요하다** — 근거:
  `~/.pub-cache/hosted/pub.dev/sign_in_with_apple-8.2.0/README.md`
  ("Prerequisites" 절: "Sign in with Apple is one of the restricted
  services which is not available for free with just an Apple ID").
- App ID에 "Sign In with Apple" capability를 등록해야 한다(Apple Developer
  포털, App ID 설정).

### Xcode capability + entitlements

`Runner` 타깃 → Signing & Capabilities → "+ Capability" → "Sign in with
Apple"을 추가하면 Xcode가 entitlements 파일에 아래를 넣는다 — 근거(예시
파일 그대로): `~/.pub-cache/hosted/pub.dev/sign_in_with_apple-8.2.0/example/ios/Runner/Runner.entitlements`.
```xml
<key>com.apple.developer.applesignin</key>
<array>
  <string>Default</string>
</array>
```
README가 명시적으로 경고한다: 이 capability가 없으면 로그인이 "시각적
신호 없이" 실패한다(예외는 던져지지만 화면엔 아무것도 안 보일 수 있다) —
근거: 같은 README의 "Your App" 절.

### 서버 검증

`clientID`로 앱(App ID/Bundle ID)에서 받은 코드를 검증해야 한다 — 서비스
ID(Service ID)는 웹/안드로이드 플로우 전용이라 iOS 전용인 이 브랜치에는
필요 없다. 근거: 같은 README의 "Your App"(iOS) 절.

---

## 검증 방법 메모

키가 생기면:
1. 위 iOS 항목을 `ios/Runner/Info.plist` + Xcode capability로 넣는다.
2. `flutter build ios --simulator --debug`로 컴파일이 여전히 되는지 먼저
   확인한다(t14에서 이미 15.0으로 올린 `IPHONEOS_DEPLOYMENT_TARGET`
   기준으로는 통과했다).
3. 실기기(카카오톡 앱 전환은 시뮬레이터에서 확인 불가)에서 세 개 공급자를
   각각 로그인 → 취소 → 재로그인 순서로 눌러 보고, 이 문서의 취소 코드
   가정(카카오는 `PlatformException(code:'CANCELED')` 또는
   `KakaoAuthException(error: AuthErrorCause.accessDenied)`, 구글은
   `GoogleSignInException(code: GoogleSignInExceptionCode.canceled)`, 애플은
   `SignInWithAppleAuthorizationException(code: AuthorizationErrorCode.canceled)`)이
   실제 기기에서도 맞는지 재확인한다 — 지금은 플랫폼 채널이 없어 단위
   테스트로 확인할 수 없었던 부분이다.
````

`app/lib/features/auth/api/apple_nonce.dart`:
```dart
import 'dart:convert';
import 'dart:math';
import 'dart:typed_data';

import 'package:crypto/crypto.dart';

/// Apple 로그인의 재생 공격(replay attack) 방지용 nonce 헬퍼.
///
/// 서버는 `sha256(rawNonce).hexdigest() == idToken.nonce`를 검증한다 —
/// Apple에는 원문 nonce의 SHA-256 16진수 해시를 건네고([hashNonce]), 서버에는
/// 원문 nonce를 그대로 보낸다([newRawNonce]가 만든 값).

/// URL-safe한 원문 nonce를 만든다. `Random.secure()`로 뽑은 32바이트를
/// base64url로 인코딩하되, 패딩(`=`)은 뗀다.
String newRawNonce({int length = 32}) {
  final random = Random.secure();
  final bytes = Uint8List.fromList(
    List<int>.generate(length, (_) => random.nextInt(256)),
  );
  return base64Url.encode(bytes).replaceAll('=', '');
}

/// [raw] nonce의 SHA-256 16진수 해시.
String hashNonce(String raw) => sha256.convert(utf8.encode(raw)).toString();
```

`app/lib/features/auth/api/apple_sign_in.dart`:
```dart
import 'package:sign_in_with_apple/sign_in_with_apple.dart';

import 'apple_nonce.dart';
import 'social_sign_in.dart';

/// Apple 로그인 어댑터. 웹뷰가 아니라 시스템 Apple 인증 시트를 쓴다.
///
/// 서버는 `sha256(rawNonce) == idToken.nonce`로 검증하므로, Apple에는 원문
/// nonce의 SHA-256 16진수 해시를 넘기고([hashNonce]), 서버에는 원문 nonce를
/// 그대로 보낸다([SocialCredential.nonce]).
class AppleSignIn implements SocialSignIn {
  const AppleSignIn();

  @override
  String get provider => 'apple';

  @override
  Future<SocialCredential?> signIn() async {
    final rawNonce = newRawNonce();
    try {
      final credential = await SignInWithApple.getAppleIDCredential(
        scopes: [
          AppleIDAuthorizationScopes.email,
          AppleIDAuthorizationScopes.fullName,
        ],
        nonce: hashNonce(rawNonce),
      );
      final displayName = [
        credential.givenName,
        credential.familyName,
      ].whereType<String>().join();
      return SocialCredential(
        provider: provider,
        token: credential.identityToken!,
        authorizationCode: credential.authorizationCode,
        nonce: rawNonce,
        displayName: displayName.isEmpty ? null : displayName,
      );
    } on SignInWithAppleAuthorizationException catch (e) {
      if (e.code == AuthorizationErrorCode.canceled) return null;
      rethrow;
    }
  }

  @override
  Future<void> disconnect() async {
    // Apple은 서버가 앱 전용 토큰을 폐기하는 방식으로 연결을 끊는다 — 이
    // 어댑터가 클라이언트에서 별도로 할 일이 없다.
  }
}
```

`app/lib/features/auth/api/google_sign_in_adapter.dart`:
```dart
import 'package:google_sign_in/google_sign_in.dart';

import 'social_sign_in.dart';

/// 구글 로그인 어댑터. `GoogleSignIn.instance.initialize`는 한 번만 부르면
/// 되므로, 이 어댑터 인스턴스 안에서 지연 초기화(lazy)하고 캐시한다.
class GoogleSignInAdapter implements SocialSignIn {
  GoogleSignInAdapter({this.clientId, this.serverClientId});

  final String? clientId;
  final String? serverClientId;

  Future<void>? _initializeFuture;

  Future<void> _ensureInitialized() {
    return _initializeFuture ??= GoogleSignIn.instance.initialize(
      clientId: clientId,
      serverClientId: serverClientId,
    );
  }

  @override
  String get provider => 'google';

  @override
  Future<SocialCredential?> signIn() async {
    await _ensureInitialized();
    try {
      final account = await GoogleSignIn.instance.authenticate();
      final idToken = account.authentication.idToken;
      if (idToken == null) {
        throw StateError('구글 로그인에서 ID 토큰을 받지 못했습니다.');
      }
      return SocialCredential(provider: provider, token: idToken);
    } on GoogleSignInException catch (e) {
      if (e.code == GoogleSignInExceptionCode.canceled) return null;
      rethrow;
    }
  }

  @override
  Future<void> disconnect() => GoogleSignIn.instance.disconnect();
}
```

`app/lib/features/auth/api/kakao_sign_in.dart`:
```dart
import 'package:flutter/services.dart';
import 'package:kakao_flutter_sdk_user/kakao_flutter_sdk_user.dart';

import 'social_sign_in.dart';

/// 카카오 로그인 어댑터. 카카오톡 앱이 있으면 앱 전환(`loginWithKakaoTalk`)으로,
/// 없으면 SDK의 시스템 인증 세션(`loginWithKakaoAccount`, iOS는
/// `ASWebAuthenticationSession`, 인앱 웹뷰가 아니다)으로 로그인한다.
///
/// 취소 신호가 흐름마다 다르다(SDK 소스로 직접 확인):
/// - 카카오톡 앱 전환 취소: `PlatformException(code: 'CANCELED')`
///   (android/ios 네이티브가 공통으로 이 코드를 보낸다).
/// - 카카오계정 동의 화면 취소: `KakaoAuthException(error:
///   AuthErrorCause.accessDenied)`.
/// - `KakaoClientException(reason: ClientErrorCause.cancelled)`도 SDK가
///   일반적인 취소 신호로 정의해 두어서, 혹시 모를 경우를 대비해 함께 잡는다.
class KakaoSignIn implements SocialSignIn {
  const KakaoSignIn();

  @override
  String get provider => 'kakao';

  @override
  Future<SocialCredential?> signIn() async {
    try {
      final installed = await isKakaoTalkInstalled();
      final token = installed
          ? await UserApi.instance.loginWithKakaoTalk()
          : await UserApi.instance.loginWithKakaoAccount();
      return SocialCredential(provider: provider, token: token.accessToken);
    } on PlatformException catch (e) {
      if (e.code == 'CANCELED') return null;
      rethrow;
    } on KakaoAuthException catch (e) {
      if (e.error == AuthErrorCause.accessDenied) return null;
      rethrow;
    } on KakaoClientException catch (e) {
      if (e.reason == ClientErrorCause.cancelled) return null;
      rethrow;
    }
  }

  @override
  Future<void> disconnect() async {
    // 카카오는 서버가 관리자 키로 연결을 끊으므로 앱에서는 할 일이 없다.
  }
}
```

`app/lib/features/auth/state/social_sign_ins.dart` — 바꾼다:
```diff
--- a/lib/features/auth/state/social_sign_ins.dart
+++ b/lib/features/auth/state/social_sign_ins.dart
@@ -1,7 +1,28 @@
+import 'package:flutter/foundation.dart';
 import 'package:flutter_riverpod/flutter_riverpod.dart';
 
+import '../../../core/proxy/providers.dart';
+import '../api/apple_sign_in.dart';
+import '../api/google_sign_in_adapter.dart';
+import '../api/kakao_sign_in.dart';
 import '../api/social_sign_in.dart';
 
-/// 사용 가능한 소셜 로그인 구현체 목록. 실제 카카오/구글/애플 구현체는
-/// 이후 슬라이스에서 채운다 — 지금은 빈 목록이다.
-final socialSignInsProvider = Provider<List<SocialSignIn>>((ref) => const []);
+/// 사용 가능한 소셜 로그인 구현체 목록. `AppConfig`(빌드 시 주입된 키)와
+/// 플랫폼에 따라 달라진다 — 키가 없는 공급자는 목록에 아예 없다(예: 개발
+/// 환경에서 키를 안 넣으면 개발용 로그인만 남는다). Apple은 안드로이드에서는
+/// 웹 플로우가 되어 버려 제공하지 않는다 — iOS에서만 넣는다.
+final socialSignInsProvider = Provider<List<SocialSignIn>>((ref) {
+  final config = ref.watch(appConfigProvider);
+  return [
+    if (config.kakaoEnabled) const KakaoSignIn(),
+    if (config.googleEnabled)
+      GoogleSignInAdapter(
+        clientId:
+            config.googleIosClientId.isEmpty ? null : config.googleIosClientId,
+        serverClientId: config.googleServerClientId,
+      ),
+    if (config.appleSignInEnabled &&
+        defaultTargetPlatform == TargetPlatform.iOS)
+      const AppleSignIn(),
+  ];
+});
```

`app/lib/main.dart` — 바꾼다:
```diff
--- a/lib/main.dart
+++ b/lib/main.dart
@@ -1,12 +1,18 @@
 import 'package:flutter/material.dart';
 import 'package:flutter_riverpod/flutter_riverpod.dart';
+import 'package:kakao_flutter_sdk_common/kakao_flutter_sdk_common.dart';
 
 import 'app.dart';
+import 'core/config/app_config.dart';
 import 'design/bridge/glass_setup.dart';
 
 Future<void> main() async {
   WidgetsFlutterBinding.ensureInitialized();
   await initializeGlass();
+  final config = AppConfig.fromEnvironment();
+  if (config.kakaoEnabled) {
+    await KakaoSdk.init(nativeAppKey: config.kakaoNativeAppKey);
+  }
   runApp(
     ProviderScope(
       // Riverpod 3의 기본 재시도를 끈다. 세션 복원 실패는 스플래시 화면이
```

- [ ] **Step 4: 통과와 네이티브 빌드를 확인한다**

Run:
```bash
flutter test && flutter analyze
flutter build ios --simulator --debug
flutter build apk --debug
```
Expected: `All tests passed!` (새 테스트 10개), `No issues found!`, 두 빌드 모두 `✓ Built …`. 빌드는 각각 수 분 걸린다. 출력이 3분 넘게 멈추면 멈추고 BLOCKED 로 보고한다.

- [ ] **Step 5: 커밋**

```bash
git add app/pubspec.yaml app/pubspec.lock app/lib app/test app/NATIVE-SETUP.md
git commit -m "feat(app): 카카오·구글·Apple 로그인 구현과 네이티브 설정 안내 (키 등록 전)"
```

### Task 15: 백엔드 재인증 — 최근 로그인 확인 (`auth_time` + `require_recent_login`)

결정 기록 003 의 출시 차단 항목을 닫는다. 지금은 훔친 액세스 토큰(15분) 하나로 공격자 수단 연결 → 피해자 수단 해제 → 계정 영구 탈취가 된다. 이 작업 뒤에는 **로그인한 지 300초 안에 받은 토큰**으로만 연결·해제·탈퇴가 된다.

**Files:**
- Modify: `backend/core/security.py`
- Modify: `backend/apps/auth/app/ports/output/token_issuer_port.py`
- Modify: `backend/apps/auth/adapter/outbound/gateways/jwt_token_issuer.py`
- Modify: `backend/apps/auth/app/services/session_issuer.py`
- Modify: `backend/apps/auth/app/use_cases/social_login_interactor.py` (`_issue` 한 곳)
- Modify: `backend/apps/auth/app/dtos/unlink_identity_dto.py`, `backend/apps/auth/app/use_cases/unlink_identity_interactor.py`
- Modify: `backend/apps/auth/adapter/inbound/api/v1/link_identity_router.py`, `unlink_identity_router.py`, `withdraw_router.py`
- Modify: `backend/tests/route_inspection.py`
- Test: `backend/apps/auth/tests/adapter/test_jwt_token_issuer.py`, `backend/apps/auth/tests/app/test_session_issuer.py`, `backend/tests/test_security.py`, `backend/apps/auth/tests/app/use_cases/test_social_login_interactor.py`, `test_unlink_identity_interactor.py`, `backend/apps/auth/tests/adapter/test_link_identity_router.py`, `test_unlink_identity_router.py`, `test_withdraw_router.py`
- Create: `backend/tests/integration/test_reauth_wiring.py`
- Modify (기존 통합 테스트·스크립트가 갱신 토큰으로 민감 요청을 보내는 곳): `backend/tests/integration/test_account_flow_wiring.py`, `backend/scripts/check_account_flow.sh`
- Docs: `docs/superpowers/specs/2026-09-20-foundation-design.md` (5.3·5.6·5.7·7절), `_docs/decisions/003-account-lifecycle.md` (출시 차단 항목 → 닫힘), `backend/apps/auth/_docs/CLAUDE.md`

**Interfaces:**
- Consumes: `core.security.get_current_user_id`, `JwtTokenIssuer(private_key, ttl_seconds, now)`, `SessionIssuer.issue(user_id, generation=None)`, `UnlinkIdentityCommand(user_id, provider)`, `tests/route_inspection.find_route_violations(app)`, 통합 픽스처 `wired`·`bearer`·`error_of` (`backend/tests/integration/support.py`)
- Produces:
  - `core.security.RECENT_LOGIN_SECONDS = 300`
  - `core.security.AccessClaims(user_id: int, auth_time: int | None)`, `decode_access_claims(token, public_key) -> AccessClaims` (`decode_access_token` 은 그대로 `int` 를 돌려준다)
  - `core.security.RecentLogin(user_id: int, auth_time: int)`, `async require_recent_login(db, credentials) -> RecentLogin` — 실패 시 `ApiError(403, "REAUTH_REQUIRED", "보안을 위해 다시 로그인해 주세요.")`
  - `TokenIssuerPort.issue_access(user_id, *, auth_time: int | None = None, fresh_login: bool = False) -> AccessToken`
  - `SessionIssuer.issue(user_id, generation=None, *, auth_time: int | None = None, fresh_login: bool = False) -> TokenPair`
  - `UnlinkIdentityCommand(user_id, provider, auth_time: int)`
  - 오류 코드 `REAUTH_REQUIRED` (403) — 앱(Task 16)이 이 코드를 본다.

규칙 (이 작업의 위협 R1~R5 — 머리말 점검표)
- `auth_time` 은 **소셜 로그인만** 새로 찍는다(`fresh_login=True` → 발급 시각). 갱신은 찍지 않는다. 해제는 요청 토큰의 값을 **그대로 물려준다**(`auth_time=<원래 값>`).
- `require_recent_login` 은 `get_current_user_id` 와 **같은 함수**로 서명·탈퇴·정지를 확인한 뒤에 `auth_time` 을 본다. 확인 순서: 401(토큰/탈퇴) → 403 `ACCOUNT_SUSPENDED` → 403 `REAUTH_REQUIRED`.
- `bool` 은 파이썬에서 `int` 의 하위 타입이다. `auth_time` 이 `True` 같은 값이면 토큰을 거절한다.

- [ ] **Step 1: 발급기의 실패하는 테스트를 쓴다**

`backend/apps/auth/tests/adapter/test_jwt_token_issuer.py` 에 더한다(기존 `test_토큰에는_역할과_권한이_들어가지_않는다` 는 그대로 통과해야 한다 — 기본 발급에는 `auth_time` 이 없다):

```python
from core.security import decode_access_claims


def test_새_로그인으로_발급하면_발급_시각이_auth_time_이다():
    private_pem, public_pem, _ = make_rsa_keypair()
    fixed = datetime(2026, 9, 22, 12, 0, tzinfo=timezone.utc)
    future_safe = lambda: fixed
    token = JwtTokenIssuer(private_pem, ttl_seconds=10**9, now=future_safe).issue_access(
        42, fresh_login=True
    ).token
    claims = jwt.get_unverified_claims(token)
    assert claims["auth_time"] == claims["iat"] == int(fixed.timestamp())
    assert decode_access_claims(token, public_pem).auth_time == int(fixed.timestamp())


def test_물려받은_auth_time_은_그대로_담긴다():
    private_pem, public_pem, _ = make_rsa_keypair()
    token = JwtTokenIssuer(private_pem, ttl_seconds=900).issue_access(42, auth_time=1_700_000_000).token
    assert decode_access_claims(token, public_pem).auth_time == 1_700_000_000


def test_기본_발급에는_auth_time_이_없다():
    private_pem, public_pem, _ = make_rsa_keypair()
    token = JwtTokenIssuer(private_pem, ttl_seconds=900).issue_access(42).token
    assert "auth_time" not in jwt.get_unverified_claims(token)
    assert decode_access_claims(token, public_pem).auth_time is None


def test_auth_time_이_정수가_아니면_거절한다():
    private_pem, public_pem, _ = make_rsa_keypair()
    now = int(datetime.now(timezone.utc).timestamp())
    for bad in (True, "1700000000", 1.5):
        forged = jwt.encode(
            {"sub": "42", "typ": "access", "exp": now + 60, "auth_time": bad},
            private_pem, algorithm="RS256",
        )
        with pytest.raises(InvalidAccessToken):
            decode_access_claims(forged, public_pem)
```

- [ ] **Step 2: 실패를 확인한다**

Run (`infra/` 에서): `docker compose run --rm backend pytest apps/auth/tests/adapter/test_jwt_token_issuer.py -q -p no:cacheprovider`
Expected: FAIL — `ImportError: cannot import name 'decode_access_claims'`

- [ ] **Step 3: 포트·발급기·검증을 구현한다**

`backend/apps/auth/app/ports/output/token_issuer_port.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from auth.app.dtos.token_dto import AccessToken


class TokenIssuerPort(ABC):
    @abstractmethod
    def issue_access(
        self, user_id: int, *, auth_time: int | None = None, fresh_login: bool = False
    ) -> AccessToken:
        """fresh_login 이면 발급 시각을 auth_time 으로 찍는다(소셜 로그인).
        auth_time 을 주면 그 값을 그대로 물려준다(수단 해제). 둘 다 없으면 찍지 않는다(갱신)."""
```

`backend/apps/auth/adapter/outbound/gateways/jwt_token_issuer.py` 의 `issue_access` 를 바꾼다:
```python
    def issue_access(
        self, user_id: int, *, auth_time: int | None = None, fresh_login: bool = False
    ) -> AccessToken:
        issued_at = self._now()
        iat = int(issued_at.timestamp())
        claims = {
            "sub": str(user_id),
            "jti": uuid4().hex,
            "typ": "access",
            "iat": iat,
            "exp": int((issued_at + timedelta(seconds=self._ttl_seconds)).timestamp()),
        }
        # 최근 로그인 확인(재인증)에 쓴다. 갱신으로 받은 토큰에는 없다.
        if fresh_login:
            claims["auth_time"] = iat
        elif auth_time is not None:
            claims["auth_time"] = auth_time
        return AccessToken(
            token=jwt.encode(claims, self._private_key, algorithm="RS256"),
            expires_in=self._ttl_seconds,
        )
```
클래스 docstring 의 "유저 ID만 담는다"를 "유저 ID 와 (소셜 로그인일 때) 로그인 시각만 담는다"로 고친다.

`backend/core/security.py` — `decode_access_token` 위에 더하고, `decode_access_token` 과 `get_current_user_id` 를 아래처럼 바꾼다:
```python
from dataclasses import dataclass
from datetime import datetime, timezone

RECENT_LOGIN_SECONDS = 300


@dataclass(frozen=True)
class AccessClaims:
    user_id: int
    auth_time: int | None  # 소셜 로그인으로 받은 토큰에만 있다 (갱신으로 받은 토큰에는 없다)


@dataclass(frozen=True)
class RecentLogin:
    user_id: int
    auth_time: int


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def decode_access_claims(token: str, public_key: str) -> AccessClaims:
    try:
        # 허용 알고리즘은 RS256 리터럴로 고정한다 (알고리즘 혼동 공격 방지).
        payload = jwt.decode(
            token, public_key, algorithms=["RS256"], options={"require_exp": True}
        )
        if payload.get("typ") != "access":
            raise ValueError("typ")
        auth_time = payload.get("auth_time")
        # bool 은 int 의 하위 타입이라 따로 거른다.
        if auth_time is not None and (isinstance(auth_time, bool) or not isinstance(auth_time, int)):
            raise ValueError("auth_time")
        return AccessClaims(user_id=int(payload["sub"]), auth_time=auth_time)
    except (JWTError, KeyError, ValueError) as exc:
        raise InvalidAccessToken() from exc


def decode_access_token(token: str, public_key: str) -> int:
    return decode_access_claims(token, public_key).user_id


async def _authenticate(db, credentials: HTTPAuthorizationCredentials | None) -> AccessClaims:
    """서명 검증 + 계정 상태 확인. 정지·탈퇴는 이미 발급된 토큰도 즉시 막는다."""
    if credentials is None:
        raise ApiError(401, "UNAUTHENTICATED", "로그인이 필요합니다.")
    try:
        claims = decode_access_claims(credentials.credentials, JWT_PUBLIC_KEY)
    except InvalidAccessToken:
        raise ApiError(401, "UNAUTHENTICATED", "토큰이 유효하지 않습니다.")
    row = (
        await db.execute(
            text("SELECT suspended_at, deleted_at FROM users WHERE id = :uid"),
            {"uid": claims.user_id},
        )
    ).first()
    if row is None or row[1] is not None:
        raise ApiError(401, "UNAUTHENTICATED", "유효하지 않은 계정입니다.")
    if row[0] is not None:
        raise ApiError(403, "ACCOUNT_SUSPENDED", "정지된 계정입니다.")
    return claims


async def get_current_user_id(
    db: DbSession,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> int:
    return (await _authenticate(db, credentials)).user_id


async def require_recent_login(
    db: DbSession,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> RecentLogin:
    """로그인 수단 연결·해제와 회원 탈퇴 앞의 재인증. 소셜 로그인한 지 RECENT_LOGIN_SECONDS 안의
    토큰만 받는다. 훔친 액세스 토큰 하나로 계정을 빼앗는 것을 막는다 — 갱신으로 받은 토큰은 통과하지 못한다."""
    claims = await _authenticate(db, credentials)
    if (
        claims.auth_time is None
        or int(_utcnow().timestamp()) - claims.auth_time > RECENT_LOGIN_SECONDS
    ):
        raise ApiError(403, "REAUTH_REQUIRED", "보안을 위해 다시 로그인해 주세요.")
    return RecentLogin(user_id=claims.user_id, auth_time=claims.auth_time)
```
`_authenticate` 의 `db` 에는 타입을 달지 않는다 — `DbSession` 은 `Depends` 가 든 `Annotated` 라 의존성 함수가 아닌 곳에 쓰면 뜻이 흐려진다.

- [ ] **Step 4: 통과를 확인한다**

Run: `docker compose run --rm backend pytest apps/auth/tests/adapter/test_jwt_token_issuer.py -q -p no:cacheprovider`
Expected: PASS (기존 5개 + 새 4개)

- [ ] **Step 5: 가드의 실패하는 테스트를 쓴다**

`backend/tests/test_security.py` 에 더한다(파일 머리의 `issuer` 픽스처와 `_insert_user`·`_bearer` 를 그대로 쓴다):
```python
from datetime import timedelta

from auth.adapter.outbound.gateways.jwt_token_issuer import JwtTokenIssuer as _Issuer


async def test_방금_로그인한_토큰은_최근_로그인으로_통과한다(db_session, issuer):
    await _insert_user(db_session, id=11)
    token = issuer.issue_access(11, fresh_login=True).token
    recent = await security.require_recent_login(db=db_session, credentials=_bearer(token))
    assert recent.user_id == 11
    assert recent.auth_time > 0


async def test_갱신으로_받은_토큰은_REAUTH_REQUIRED_다(db_session, issuer):
    await _insert_user(db_session, id=12)
    token = issuer.issue_access(12).token   # auth_time 없음 = 갱신이 발급한 토큰
    with pytest.raises(ApiError) as exc:
        await security.require_recent_login(db=db_session, credentials=_bearer(token))
    assert (exc.value.status_code, exc.value.code) == (403, "REAUTH_REQUIRED")


async def test_로그인한_지_오래된_토큰은_403_이다(db_session, monkeypatch):
    private_pem, public_pem, _ = make_rsa_keypair()
    monkeypatch.setattr(security, "JWT_PUBLIC_KEY", public_pem)
    await _insert_user(db_session, id=13)
    long_ago = lambda: datetime.now(timezone.utc) - timedelta(seconds=security.RECENT_LOGIN_SECONDS + 1)
    # 만료는 아직 멀었지만(ttl 900초) 로그인한 지 301초가 지났다.
    token = _Issuer(private_pem, ttl_seconds=900, now=long_ago).issue_access(13, fresh_login=True).token
    with pytest.raises(ApiError) as exc:
        await security.require_recent_login(db=db_session, credentials=_bearer(token))
    assert (exc.value.status_code, exc.value.code) == (403, "REAUTH_REQUIRED")


async def test_경계_안쪽의_토큰은_통과한다(db_session, monkeypatch):
    private_pem, public_pem, _ = make_rsa_keypair()
    monkeypatch.setattr(security, "JWT_PUBLIC_KEY", public_pem)
    await _insert_user(db_session, id=14)
    almost = lambda: datetime.now(timezone.utc) - timedelta(seconds=security.RECENT_LOGIN_SECONDS - 5)
    token = _Issuer(private_pem, ttl_seconds=900, now=almost).issue_access(14, fresh_login=True).token
    assert (await security.require_recent_login(db=db_session, credentials=_bearer(token))).user_id == 14


async def test_정지된_계정은_최근_로그인이어도_403_ACCOUNT_SUSPENDED_다(db_session, issuer):
    await _insert_user(db_session, id=15, suspended_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    token = issuer.issue_access(15, fresh_login=True).token
    with pytest.raises(ApiError) as exc:
        await security.require_recent_login(db=db_session, credentials=_bearer(token))
    assert (exc.value.status_code, exc.value.code) == (403, "ACCOUNT_SUSPENDED")


async def test_탈퇴한_계정은_최근_로그인이어도_401_이다(db_session, issuer):
    await _insert_user(db_session, id=16, deleted_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    token = issuer.issue_access(16, fresh_login=True).token
    with pytest.raises(ApiError) as exc:
        await security.require_recent_login(db=db_session, credentials=_bearer(token))
    assert exc.value.status_code == 401
```

Run: `docker compose run --rm backend pytest tests/test_security.py -q -p no:cacheprovider -m integration`
Expected: PASS — Step 3 에서 가드를 이미 구현했다. **판별력을 확인한다**: `require_recent_login` 의 `or int(_utcnow()…) > RECENT_LOGIN_SECONDS` 줄을 잠깐 지우면 `test_로그인한_지_오래된_토큰은_403_이다` 가 실패해야 한다. 확인 뒤 `git checkout -- backend/core/security.py` 가 아니라 **직접 되돌린다**(이 파일은 아직 커밋 전이다).

- [ ] **Step 6: 발급 절차 — 로그인은 찍고, 갱신은 찍지 않고, 해제는 물려준다**

`backend/apps/auth/tests/app/test_session_issuer.py` — 스텁이 받은 인자를 기록하게 바꾸고 테스트를 더한다:
```python
class _StubIssuer:
    def __init__(self):
        self.seen = []

    def issue_access(self, user_id, *, auth_time=None, fresh_login=False):
        self.seen.append((user_id, auth_time, fresh_login))
        return AccessToken(token=f"access-for-{user_id}", expires_in=900)


async def test_기본_발급은_로그인_시각을_찍지_않는다():
    issuer = _StubIssuer()
    await SessionIssuer(issuer, _StubStore()).issue(5, generation=2)
    assert issuer.seen == [(5, None, False)]


async def test_새_로그인과_물려받은_시각을_발급기에_그대로_넘긴다():
    issuer = _StubIssuer()
    sessions = SessionIssuer(issuer, _StubStore())
    await sessions.issue(5, fresh_login=True)
    await sessions.issue(5, auth_time=1_700_000_000)
    assert issuer.seen == [(5, None, True), (5, 1_700_000_000, False)]
```
(기존 세 테스트의 `SessionIssuer(_StubIssuer(), store)` 는 그대로 동작한다.)

`backend/apps/auth/app/services/session_issuer.py` 의 `issue`:
```python
    async def issue(
        self,
        user_id: int,
        generation: int | None = None,
        *,
        auth_time: int | None = None,
        fresh_login: bool = False,
    ) -> TokenPair:
        """generation 이 없으면 현재 세대로 발급한다(로그인). 갱신은 꺼낼 때 받은 세대를 넘긴다 —
        그 사이 모든 세션 폐기가 끼어들었다면 새 토큰도 함께 무효가 되어야 하기 때문이다.
        fresh_login 은 소셜 로그인만 켠다. auth_time 은 수단 해제가 요청 토큰의 값을 물려줄 때만 쓴다."""
        access = self._token_issuer.issue_access(
            user_id, auth_time=auth_time, fresh_login=fresh_login
        )
```
(그 아래는 그대로다.)

`backend/apps/auth/app/use_cases/social_login_interactor.py` 의 `_issue`:
```python
        tokens = await self._sessions.issue(user_id, fresh_login=True)
```
`backend/apps/auth/tests/app/use_cases/test_social_login_interactor.py` 의 세션 스텁 `issue` 가 `fresh_login` 을 기록하게 하고(`async def issue(self, user_id, generation=None, *, auth_time=None, fresh_login=False)`), 기존 로그인 성공 테스트에 **`fresh_login is True` 로 불렸다**는 단언을 더한다. 스텁의 기록 형식은 그 파일의 기존 방식을 따른다.

`backend/apps/auth/app/use_cases/refresh_token_interactor.py` 는 **바꾸지 않는다** — 갱신은 `sessions.issue(user_id, generation)` 만 부르므로 로그인 시각이 찍히지 않는다. 이것을 테스트로 못 박는다. `backend/apps/auth/tests/app/use_cases/test_refresh_token_interactor.py` 의 세션 스텁을 아래로 바꾸고 테스트를 하나 더한다(기존 테스트의 `sessions.issued_for == [(5, 4)]` 단언은 그대로 통과한다):
```python
class _StubSessions:
    def __init__(self):
        self.issued_for = []
        self.login_marks = []

    async def issue(self, user_id, generation=None, *, auth_time=None, fresh_login=False):
        self.issued_for.append((user_id, generation))
        self.login_marks.append((auth_time, fresh_login))
        return TokenPair("new-access", "new-refresh", 900)


async def test_갱신은_로그인_시각을_찍지_않는다():
    interactor, _, sessions = _run(RefreshLookup(RefreshStatus.ACTIVE, 5, 4), _user())
    await interactor.refresh(RefreshTokenCommand("5.old-refresh"))
    assert sessions.login_marks == [(None, False)]
```

`backend/apps/auth/app/dtos/unlink_identity_dto.py`:
```python
@dataclass(frozen=True)
class UnlinkIdentityCommand:
    user_id: int
    provider: str
    auth_time: int   # 요청 토큰의 로그인 시각. 새 토큰이 그대로 물려받는다 (해제를 되풀이해 늘릴 수 없게)
```

`backend/apps/auth/app/use_cases/unlink_identity_interactor.py` 의 발급 줄:
```python
        tokens = await self._sessions.issue(user.id, auth_time=command.auth_time)
```

`backend/apps/auth/tests/app/use_cases/test_unlink_identity_interactor.py` — 세션 스텁의 기록을 `f"issue:{user_id}:{generation}:{auth_time}:{fresh_login}"` 로 바꾸고, 명령을 `UnlinkIdentityCommand(user_id=5, provider="apple", auth_time=1_700_000_000)` 로 만든다. 성공 경로의 기대값은 다음과 같다:
```python
    assert calls == [
        "lock:5", "list_revocations:5", "delete:5:apple", "revoke_all:5",
        "issue:5:None:1700000000:False",
    ]
```
이 한 줄이 위협 R2 를 못 박는다: 해제는 `fresh_login=True` 로 발급하지 않고 원래 시각을 물려준다.

Run: `docker compose run --rm backend pytest apps/auth/tests/app -q -p no:cacheprovider`
Expected: PASS

- [ ] **Step 7: 세 라우터에 가드를 단다**

`link_identity_router.py`:
```python
from core.security import RecentLogin, require_recent_login
...
async def link_identity(
    body: LinkIdentityRequestSchema,
    recent: RecentLogin = Depends(require_recent_login),
    use_case: LinkIdentityUseCase = Depends(get_link_identity_use_case),
) -> IdentitiesResponseSchema:
    result = await use_case.link(
        LinkIdentityCommand(
            user_id=recent.user_id,
```
`unlink_identity_router.py`:
```python
    recent: RecentLogin = Depends(require_recent_login),
    ...
    result = await use_case.unlink(
        UnlinkIdentityCommand(
            user_id=recent.user_id, provider=provider, auth_time=recent.auth_time
        )
    )
```
`withdraw_router.py`:
```python
    recent: RecentLogin = Depends(require_recent_login),
    ...
        WithdrawCommand(
            user_id=recent.user_id,
```
세 파일 모두 `get_current_user_id` import 를 지운다(이제 쓰지 않는다).

세 라우터 테스트(`test_link_identity_router.py`, `test_unlink_identity_router.py`, `test_withdraw_router.py`)는 `app.dependency_overrides[get_current_user_id] = lambda: user_id` 를 쓰고 있다. 이것을 다음으로 바꾼다:
```python
from core.security import RecentLogin, require_recent_login
...
        app.dependency_overrides[require_recent_login] = lambda: RecentLogin(user_id=user_id, auth_time=1_700_000_000)
```
해제 라우터 테스트의 성공 경로에 **명령에 `auth_time == 1_700_000_000` 이 실렸다**는 단언을 더한다(`stub.commands[0].auth_time`). "로그인하지 않으면 401" 테스트는 override 를 걸지 않는 기존 분기를 그대로 쓴다.

- [ ] **Step 8: 구조 테스트 — 민감 경로는 가드를 거친다**

`backend/tests/route_inspection.py`:
```python
from core.security import require_recent_login
...
# 계정을 빼앗는 데 쓰일 수 있는 경로. 새로 더하는 민감 경로도 여기에 적는다.
_RECENT_LOGIN_PREFIXES = ("/v1/auth/identities", "/v1/auth/account")
...
        if path.startswith(_RECENT_LOGIN_PREFIXES) and require_recent_login not in calls:
            violations.append(f"{path}: 민감한 계정 경로인데 require_recent_login 을 거치지 않는다")
```
(`find_route_violations` 의 `for` 안, 운영자 표면 검사 아래에 둔다.)

**판별력 확인**: `withdraw_router.py` 의 가드를 잠깐 `get_current_user_id` 로 되돌리면 `docker compose run --rm backend pytest tests/integration/test_route_wiring.py -q -p no:cacheprovider -m integration` 이 `/v1/auth/account: 민감한 계정 경로인데 …` 로 실패해야 한다. 확인 뒤 직접 되돌린다.

- [ ] **Step 9: 실제 배선 통합 테스트**

`backend/tests/integration/test_reauth_wiring.py`:
```python
"""재인증(최근 로그인 확인)이 실제 배선에서 도는지 본다."""
import pytest

from tests.integration.support import bearer, error_of

pytestmark = pytest.mark.integration


async def _refresh(wired, login):
    response = await wired.auth.post("/v1/auth/refresh", json={"refresh_token": login["refresh_token"]})
    assert response.status_code == 200, response.text
    return response.json()


async def test_방금_로그인한_토큰으로는_수단을_연결할_수_있다(wired):
    login = await wired.login("두부")
    response = await wired.auth.post(
        "/v1/auth/identities", json={"provider": "dev", "token": "두부"},
        headers=bearer(login["access_token"]),
    )
    # dev 수단은 이미 있으므로 409 다 — 403 REAUTH_REQUIRED 가 아니라는 것이 요점이다.
    assert error_of(response) == (409, "PROVIDER_ALREADY_LINKED")


async def test_갱신으로_받은_토큰은_연결_해제_탈퇴_모두_REAUTH_REQUIRED_다(wired):
    login = await wired.login("두부")
    refreshed = await _refresh(wired, login)
    headers = bearer(refreshed["access_token"])
    link = await wired.auth.post("/v1/auth/identities", json={"provider": "dev", "token": "두부"}, headers=headers)
    unlink = await wired.auth.delete("/v1/auth/identities/dev", headers=headers)
    withdraw = await wired.auth.delete("/v1/auth/account", headers=headers)
    assert [error_of(r) for r in (link, unlink, withdraw)] == [(403, "REAUTH_REQUIRED")] * 3
    # 아무것도 바뀌지 않았다: 같은 토큰으로 내 정보가 그대로 나온다.
    me = await wired.api.get("/v1/me", headers=headers)
    assert me.status_code == 200 and me.json()["identities"] == ["dev"]


async def test_다시_로그인하면_탈퇴할_수_있다(wired):
    login = await wired.login("두부")
    await _refresh(wired, login)
    again = await wired.login("두부")   # 재인증 = 소셜 로그인을 한 번 더
    response = await wired.auth.delete("/v1/auth/account", headers=bearer(again["access_token"]))
    assert response.status_code == 204
```
`error_of` 가 `support.py` 에 있는 대로 `(status_code, code)` 를 돌려주는지 읽고 쓴다.

Run: `docker compose run --rm backend pytest tests/integration/test_reauth_wiring.py -q -p no:cacheprovider -m integration`
Expected: PASS (3개)

- [ ] **Step 10: 기존 통합 테스트와 확인 스크립트를 맞춘다**

Run: `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration`
갱신으로 받은 토큰이나 해제 뒤 물려받은 토큰으로 민감 요청을 보내던 테스트가 `REAUTH_REQUIRED` 로 실패할 수 있다. 규칙은 하나다: **테스트가 검증하려는 것이 재인증이 아니면, 민감 요청 바로 앞에서 `wired.login(같은 이름)` 으로 새 토큰을 받아 쓴다.** 단언을 약하게 만들지 않는다. 해제 응답의 새 토큰은 원래 `auth_time` 을 물려받으므로 5분 안에서는 그대로 통과한다 — 이것을 확인하는 테스트를 `test_reauth_wiring.py` 에 하나 더한다:
```python
async def test_해제가_준_토큰은_원래_로그인_시각을_물려받는다(wired, fake_kakao):
    from jose import jwt
    login = await wired.login("두부")
    headers = bearer(login["access_token"])
    linked = await wired.auth.post(
        "/v1/auth/identities", json={"provider": "kakao", "token": "kakao-token-for-dubu"}, headers=headers
    )
    assert linked.status_code == 200, linked.text
    unlinked = await wired.auth.delete("/v1/auth/identities/kakao", headers=headers)
    assert unlinked.status_code == 200, unlinked.text
    before = jwt.get_unverified_claims(login["access_token"])["auth_time"]
    after = jwt.get_unverified_claims(unlinked.json()["access_token"])["auth_time"]
    same = before == after          # 토큰 값이 단언 메시지에 찍히지 않게 불리언으로 비교한다
    assert same
```
`fake_kakao` 픽스처가 받는 토큰 형식은 `backend/tests/integration/conftest.py` 와 `test_account_flow_wiring.py` 의 기존 사용처를 읽고 맞춘다.

`backend/scripts/check_account_flow.sh` 를 돌려 본다(`infra/` 에서 `docker compose restart backend auth` 뒤 `bash ../backend/scripts/check_account_flow.sh`). 중간에 갱신한 토큰으로 민감 요청을 보내 403 이 나오면 그 앞에서 다시 로그인하게 고치고, 스크립트에 "갱신으로 받은 토큰은 REAUTH_REQUIRED" 확인 한 단계를 더한다. 토큰을 화면에 찍지 않는다.

- [ ] **Step 11: 문서**

- 설계 문서 5.3절: 액세스 토큰의 클레임에 `auth_time`(소셜 로그인만)을 더하고 "연결·해제·탈퇴는 로그인 300초 이내의 토큰만 받는다. 아니면 403 `REAUTH_REQUIRED`. 해제가 준 새 토큰은 원래 값을 물려받는다"를 적는다. 5.6·5.7절의 각 흐름 첫 단계에 "최근 로그인 확인"을 더한다. 7절의 403 코드 목록에 `REAUTH_REQUIRED` 를 더한다.
- `_docs/decisions/003-account-lifecycle.md` 의 출시 차단 항목 "재인증"에 "→ 계획 3 Task 15 에서 닫음(최근 로그인 확인, 300초)"을 적고, 남는 틈을 정확히 적는다: **로그인 직후 300초 안에 훔친 토큰은 여전히 통한다**(창이 15분 → 5분, 그리고 "로그인 직후"로 좁아졌다).
- `backend/apps/auth/_docs/CLAUDE.md`: "민감한 계정 경로를 더할 때는 `require_recent_login` 을 쓰고 `tests/route_inspection.py` 의 `_RECENT_LOGIN_PREFIXES` 에 경로를 적는다."

- [ ] **Step 12: 전체 확인과 커밋**

Run:
```bash
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration
docker compose run --rm --no-deps backend lint-imports --config .importlinter
```
Expected: 전부 통과, `Contracts: 6 kept, 0 broken.`

```bash
git add backend docs _docs
git commit -m "feat(auth): 연결·해제·탈퇴 앞에 최근 로그인 확인을 둔다 (REAUTH_REQUIRED)"
```

### Task 16: 앱의 재인증 — `REAUTH_REQUIRED` 를 받으면 한 번 더 로그인하고 한 번만 다시 보낸다

**Files:**
- Create: `app/lib/features/account/state/reauth.dart`
- Modify: `app/lib/features/account/state/account_controller.dart`, `withdraw_controller.dart`, `app/lib/features/account/screens/account_screen.dart`, `withdraw_screen.dart`, `app/lib/l10n/app_strings.dart`, `app/test/features/account/screens/withdraw_screen_test.dart`
- Test: `app/test/features/account/state/reauth_test.dart`

**Interfaces:**
- Consumes: Task 15 의 오류 코드 `REAUTH_REQUIRED`(403), `AuthApi.socialLogin`·`logout`(Task 6), `TokenStore`, `socialSignInsProvider`, `AccountApi`(Task 12)
- Produces: `ReauthCoordinator.run<T>(Future<T> Function() action)`, `ReauthPromptHolder`·`reauthPromptProvider`, `ReauthMismatchException`

동작 규칙 (점검표 S6)
1. `action` 을 돌린다. `ApiException.code == 'REAUTH_REQUIRED'` 가 아니면 그대로 끝이다.
2. 프롬프트(시트 "보안을 위해 다시 로그인해 주세요" — **이 계정에 연결된 수단** 가운데 이 기기에서 쓸 수 있는 것만, `dev` 는 이름 입력)를 띄운다. 닫으면(`null`) **`/v1/auth/social` 을 부르지 않고** 원래의 `REAUTH_REQUIRED` 오류를 다시 던진다.
3. 자격 증명을 받으면 `authApi.socialLogin`. **응답의 `user_id` 가 지금 로그인한 유저와 다르면**: 그 세션은 남의 계정 것이다 — `authApi.logout(그 리프레시 토큰)` 을 최선으로 부르고 `ReauthMismatchException` 을 던진다. **저장된 토큰은 건드리지 않는다.** 이 확인이 없으면 재인증 시트에서 다른 계정으로 로그인한 순간 앱의 세션이 조용히 남의 계정으로 바뀐다.
4. 같으면 새 토큰을 저장하고 `action` 을 **한 번만** 더 돌린다. 또 `REAUTH_REQUIRED` 면 그대로 던진다(루프 없음).
5. 감싸는 곳은 정확히 셋이다: 연결, 해제, 탈퇴(첫 요청과 확인 요청 둘 다). 해제가 재인증을 거쳐도 **해제 응답의 토큰이 마지막에 저장된다**(S5 가 그대로 지켜진다).
6. `ReauthMismatchException` 의 문구는 화면이 직접 고른다. `core/error/error_messages.dart` 는 `features/` 를 모른다.

실험에서 걸린 함정
- 위젯의 `dispose()` 안에서 `ref.read` 를 부르면 Riverpod 이 `StateError` 를 던진다. `initState` 에서 받은 `ReauthPromptHolder` 를 필드에 잡아 두고 `dispose()` 에서는 그 필드만 비운다.
- 재인증 시트가 떠 있는 동안 버튼은 계속 바쁜 상태(스피너)다. 그 구간의 위젯 테스트는 `pumpAndSettle` 이 아니라 `pump(duration)` 을 쓴다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`app/test/features/account/screens/withdraw_screen_test.dart` — 바꾼다:
```diff
--- a/test/features/account/screens/withdraw_screen_test.dart
+++ b/test/features/account/screens/withdraw_screen_test.dart
@@ -4,6 +4,7 @@
 import 'dart:convert';
 import 'dart:typed_data';
 
+import 'package:chagocnote/core/config/app_config.dart';
 import 'package:chagocnote/core/proxy/api_client.dart';
 import 'package:chagocnote/core/proxy/providers.dart';
 import 'package:chagocnote/core/router/app_router.dart';
@@ -37,8 +38,9 @@ final Finder _submitButton = find.byWidgetPredicate(
 
 ({ProviderContainer container, FakeHttpClientAdapter adapter}) _setUp(
   FakeSessionGateway gateway,
-  FakeHandler handle,
-) {
+  FakeHandler handle, {
+  AppConfig? config,
+}) {
   final adapter = FakeHttpClientAdapter(handle);
   final dio = Dio(BaseOptions())..httpClientAdapter = adapter;
   final refreshDio = Dio(BaseOptions())..httpClientAdapter = adapter;
@@ -48,6 +50,7 @@ final Finder _submitButton = find.byWidgetPredicate(
     overrides: [
       sessionGatewayProvider.overrideWithValue(gateway),
       tokenStoreProvider.overrideWithValue(tokenStore),
+      if (config != null) appConfigProvider.overrideWithValue(config),
       apiClientProvider.overrideWith(
         (ref) => ApiClient(
           tokenStore: tokenStore,
@@ -235,6 +238,66 @@ void main() {
     expect(find.text(AppStrings.goToMembers), findsOneWidget);
     expect(setup.adapter.requests, hasLength(1));
   });
+
+  testWidgets('REAUTH_REQUIRED 를 받으면 재인증 시트에서 dev 로 다시 로그인해 탈퇴를 끝낸다', (
+    tester,
+  ) async {
+    final gateway = FakeSessionGateway()..meOnRestore = _me(['dev']);
+    var withdrawCallCount = 0;
+    final setup = _setUp(
+      gateway,
+      (options, body) {
+        if (options.path == '/v1/auth/social') {
+          expect(jsonDecode(utf8.decode(body!)), {
+            'provider': 'dev',
+            'token': '민석',
+          });
+          return const FakeResponse(
+            statusCode: 200,
+            data: {
+              'access_token': 'reauth-access',
+              'refresh_token': 'reauth-refresh',
+              'token_type': 'Bearer',
+              'expires_in': 3600,
+              'user_id': 1,
+              'is_new_user': false,
+            },
+          );
+        }
+        if (options.path == '/v1/auth/account') {
+          withdrawCallCount++;
+          if (withdrawCallCount == 1) {
+            return const FakeResponse(
+              statusCode: 403,
+              data: {'code': 'REAUTH_REQUIRED', 'message': '다시 로그인해 주세요'},
+            );
+          }
+          return const FakeResponse(statusCode: 204);
+        }
+        fail('예상하지 못한 요청: ${options.path}');
+      },
+      config: const AppConfig(apiBaseUrl: '', appEnv: 'dev'),
+    );
+    addTearDown(setup.container.dispose);
+
+    await _openWithdrawScreen(tester, setup.container);
+    await tester.tap(find.text(AppStrings.withdrawConfirmCheckbox));
+    await tester.pumpAndSettle();
+    await tester.tap(_submitButton);
+    // 재인증 시트를 기다리는 동안 탈퇴 버튼이 계속 busy(스피너)라
+    // pumpAndSettle이 절대 안 멈춘다 — 정해진 만큼만 pump 한다.
+    await tester.pump(const Duration(milliseconds: 50));
+    await tester.pump(const Duration(milliseconds: 1000));
+
+    expect(find.text(AppStrings.reauthPromptTitle), findsOneWidget);
+    await tester.enterText(find.byType(TextField), '민석');
+    await tester.tap(find.text(AppStrings.devSignIn));
+    await tester.pump(const Duration(milliseconds: 50));
+    await tester.pump(const Duration(milliseconds: 1000));
+
+    expect(withdrawCallCount, 2);
+    expect(find.byKey(ScreenKeys.login), findsOneWidget);
+  });
 }
 
 class _NoopTokenStore implements TokenStore {
```

`app/test/features/account/state/reauth_test.dart`:
```dart
// ReauthCoordinator를 위젯 트리 없이 ProviderContainer로 직접 검증한다.
// 프롬프트는 함수(콜백)로 갈아 끼워서, 시트 UI 없이도 "재인증 성공/취소/
// 다른 계정" 분기를 확인한다. 화면(시트 UI) 쪽은 withdraw_screen_test.dart의
// 위젯 테스트에서 본다.
import 'dart:convert';

import 'package:chagocnote/core/error/api_exception.dart';
import 'package:chagocnote/core/proxy/api_client.dart';
import 'package:chagocnote/core/proxy/providers.dart';
import 'package:chagocnote/core/storage/token_store.dart';
import 'package:chagocnote/features/account/state/account_controller.dart';
import 'package:chagocnote/features/account/state/reauth.dart';
import 'package:chagocnote/features/auth/api/social_sign_in.dart';
import 'package:chagocnote/features/auth/state/session.dart';
import 'package:chagocnote/features/auth/state/session_controller.dart';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/fake_http_client_adapter.dart';
import '../../../support/fake_session_gateway.dart';

Me _me(List<String> identities, {int id = 1}) => Me(
      id: id,
      displayName: '민석',
      profileImageUrl: null,
      identities: identities,
      shops: const [],
    );

const _socialLoginOk = {
  'token_type': 'Bearer',
  'expires_in': 3600,
  'is_new_user': false,
};

({ProviderContainer container, FakeHttpClientAdapter adapter, TokenStore tokenStore})
    _setUp({
  required FakeSessionGateway gateway,
  required FakeHandler handle,
  ReauthPrompt? prompt,
}) {
  final adapter = FakeHttpClientAdapter(handle);
  final dio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final refreshDio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final tokenStore = MemoryTokenStore();
  final container = ProviderContainer.test(
    retry: (retryCount, error) => null,
    overrides: [
      sessionGatewayProvider.overrideWithValue(gateway),
      tokenStoreProvider.overrideWithValue(tokenStore),
      apiClientProvider.overrideWith(
        (ref) => ApiClient(
          tokenStore: tokenStore,
          dio: dio,
          refreshDio: refreshDio,
          onSessionEnded: ref.read(sessionEndedSignalProvider).fire,
        ),
      ),
    ],
  );
  if (prompt != null) container.read(reauthPromptProvider).prompt = prompt;
  return (container: container, adapter: adapter, tokenStore: tokenStore);
}

void main() {
  test('REAUTH_REQUIRED → 프롬프트 → 재로그인 → 재시도가 새 토큰으로 성공한다', () async {
    var probeCallCount = 0;
    String? authHeaderOnRetry;
    final gateway = FakeSessionGateway()..meOnRestore = _me(['apple']);
    final setup = _setUp(
      gateway: gateway,
      handle: (options, body) {
        if (options.path == '/v1/auth/social') {
          return const FakeResponse(
            statusCode: 200,
            data: {
              'access_token': 'new-access',
              'refresh_token': 'new-refresh',
              'user_id': 1,
              ..._socialLoginOk,
            },
          );
        }
        if (options.path == '/probe') {
          probeCallCount++;
          if (probeCallCount == 1) {
            return const FakeResponse(
              statusCode: 403,
              data: {'code': 'REAUTH_REQUIRED', 'message': '다시 로그인'},
            );
          }
          authHeaderOnRetry = options.headers['Authorization'] as String?;
          return const FakeResponse(statusCode: 200, data: {'ok': true});
        }
        fail('예상하지 못한 요청: ${options.path}');
      },
      prompt: (linked) async =>
          const SocialCredential(provider: 'apple', token: 'tok'),
    );
    addTearDown(setup.container.dispose);
    await setup.container.read(sessionControllerProvider.future);

    final result = await setup.container.read(reauthCoordinatorProvider).run(
          () => setup.container.read(apiClientProvider).get('/probe'),
        );

    expect(result, {'ok': true});
    expect(probeCallCount, 2);
    expect(authHeaderOnRetry, 'Bearer new-access');
  });

  test('S6 — 다른 계정으로 재로그인하면 저장된 토큰은 그대로고 그 세션은 로그아웃된다', () async {
    String? loggedOutRefreshToken;
    final gateway = FakeSessionGateway()..meOnRestore = _me(['apple'], id: 1);
    final setup = _setUp(
      gateway: gateway,
      handle: (options, body) {
        if (options.path == '/v1/auth/social') {
          return const FakeResponse(
            statusCode: 200,
            data: {
              'access_token': 'other-access',
              'refresh_token': 'other-refresh',
              'user_id': 999, // 다른 계정
              ..._socialLoginOk,
            },
          );
        }
        if (options.path == '/v1/auth/logout') {
          final payload = jsonDecode(utf8.decode(body!)) as Map;
          loggedOutRefreshToken = payload['refresh_token'] as String;
          return const FakeResponse(statusCode: 204);
        }
        if (options.path == '/probe') {
          return const FakeResponse(
            statusCode: 403,
            data: {'code': 'REAUTH_REQUIRED', 'message': '다시 로그인'},
          );
        }
        fail('예상하지 못한 요청: ${options.path}');
      },
      prompt: (linked) async =>
          const SocialCredential(provider: 'apple', token: 'tok'),
    );
    addTearDown(setup.container.dispose);
    await setup.container.read(sessionControllerProvider.future);
    await setup.tokenStore.save(access: 'own-access', refresh: 'own-refresh');
    final accessBefore = await setup.tokenStore.readAccess();
    final refreshBefore = await setup.tokenStore.readRefresh();

    await expectLater(
      setup.container.read(reauthCoordinatorProvider).run(
            () => setup.container.read(apiClientProvider).get('/probe'),
          ),
      throwsA(isA<ReauthMismatchException>()),
    );

    // 토큰 값 자체는 절대 출력하지 않는다 — 불리언 비교로만 "안 바뀜"을 본다.
    expect(await setup.tokenStore.readAccess() == accessBefore, isTrue);
    expect(await setup.tokenStore.readRefresh() == refreshBefore, isTrue);
    expect(loggedOutRefreshToken, 'other-refresh');
  });

  test('프롬프트를 닫으면(취소) 재로그인 요청 없이 원래 REAUTH_REQUIRED 문구가 그대로 올라온다', () async {
    final gateway = FakeSessionGateway()..meOnRestore = _me(['apple']);
    final setup = _setUp(
      gateway: gateway,
      handle: (options, body) {
        if (options.path == '/probe') {
          return const FakeResponse(
            statusCode: 403,
            data: {'code': 'REAUTH_REQUIRED', 'message': '다시 로그인해 주세요'},
          );
        }
        fail('예상하지 못한 요청: ${options.path}');
      },
      prompt: (linked) async => null, // 사용자가 시트를 닫음
    );
    addTearDown(setup.container.dispose);
    await setup.container.read(sessionControllerProvider.future);

    await expectLater(
      setup.container.read(reauthCoordinatorProvider).run(
            () => setup.container.read(apiClientProvider).get('/probe'),
          ),
      throwsA(
        isA<ApiException>()
            .having((e) => e.code, 'code', 'REAUTH_REQUIRED')
            .having((e) => e.message, 'message', '다시 로그인해 주세요'),
      ),
    );
    expect(
      setup.adapter.requests.where((r) => r.path == '/v1/auth/social'),
      isEmpty,
    );
  });

  test('재시도에서도 REAUTH_REQUIRED 면 다시 프롬프트하지 않고 그대로 던진다(루프 없음)', () async {
    var promptCallCount = 0;
    final gateway = FakeSessionGateway()..meOnRestore = _me(['apple']);
    final setup = _setUp(
      gateway: gateway,
      handle: (options, body) {
        if (options.path == '/v1/auth/social') {
          return const FakeResponse(
            statusCode: 200,
            data: {
              'access_token': 'new-access',
              'refresh_token': 'new-refresh',
              'user_id': 1,
              ..._socialLoginOk,
            },
          );
        }
        if (options.path == '/probe') {
          return const FakeResponse(
            statusCode: 403,
            data: {'code': 'REAUTH_REQUIRED', 'message': '다시 로그인'},
          );
        }
        fail('예상하지 못한 요청: ${options.path}');
      },
      prompt: (linked) async {
        promptCallCount++;
        return const SocialCredential(provider: 'apple', token: 'tok');
      },
    );
    addTearDown(setup.container.dispose);
    await setup.container.read(sessionControllerProvider.future);

    await expectLater(
      setup.container.read(reauthCoordinatorProvider).run(
            () => setup.container.read(apiClientProvider).get('/probe'),
          ),
      throwsA(isA<ApiException>().having((e) => e.code, 'code', 'REAUTH_REQUIRED')),
    );
    expect(promptCallCount, 1);
  });

  test('unlink 이 재인증을 거쳐도 해제 응답의 토큰이 마지막에 저장된다(이긴다)', () async {
    var unlinkCallCount = 0;
    final gateway = FakeSessionGateway()
      ..meOnRestore = _me(['apple', 'kakao'])
      ..meOnRefresh = _me(['apple']);
    final setup = _setUp(
      gateway: gateway,
      handle: (options, body) {
        if (options.path == '/v1/auth/social') {
          return const FakeResponse(
            statusCode: 200,
            data: {
              'access_token': 'reauth-access',
              'refresh_token': 'reauth-refresh',
              'user_id': 1,
              ..._socialLoginOk,
            },
          );
        }
        if (options.path == '/v1/auth/identities/kakao' &&
            options.method == 'DELETE') {
          unlinkCallCount++;
          if (unlinkCallCount == 1) {
            return const FakeResponse(
              statusCode: 403,
              data: {'code': 'REAUTH_REQUIRED', 'message': '다시 로그인'},
            );
          }
          return const FakeResponse(
            statusCode: 200,
            data: {
              'identities': ['apple'],
              'access_token': 'unlink-access',
              'refresh_token': 'unlink-refresh',
              'token_type': 'Bearer',
              'expires_in': 3600,
            },
          );
        }
        fail('예상하지 못한 요청: ${options.method} ${options.path}');
      },
      prompt: (linked) async =>
          const SocialCredential(provider: 'apple', token: 'tok'),
    );
    addTearDown(setup.container.dispose);
    await setup.container.read(sessionControllerProvider.future);

    await setup.container.read(accountControllerProvider.notifier).unlink('kakao');

    expect(unlinkCallCount, 2);
    expect(await setup.tokenStore.readAccess(), 'unlink-access');
    expect(await setup.tokenStore.readRefresh(), 'unlink-refresh');
  });
}
```

Run: `flutter test test/features/account`
Expected: FAIL — `reauth.dart` 가 없다.

- [ ] **Step 2: 구현한다**

`app/lib/features/account/screens/account_screen.dart` — 바꾼다:
```diff
--- a/lib/features/account/screens/account_screen.dart
+++ b/lib/features/account/screens/account_screen.dart
@@ -17,6 +17,7 @@ import '../../auth/state/session.dart';
 import '../../auth/state/session_controller.dart';
 import '../../auth/state/social_sign_ins.dart';
 import '../state/account_controller.dart';
+import '../state/reauth.dart';
 
 /// 계정 화면 — 로그인 수단 연결/해제, 로그아웃, 회원 탈퇴로 가는 입구.
 class AccountScreen extends ConsumerStatefulWidget {
@@ -31,9 +32,21 @@ class _AccountScreenState extends ConsumerState<AccountScreen> {
   bool _busy = false;
   String? _errorText;
   String? _devNameError;
+  late final ReauthPromptHolder _reauthPromptHolder;
+
+  @override
+  void initState() {
+    super.initState();
+    _reauthPromptHolder = ref.read(reauthPromptProvider)
+      ..prompt = (linked) => showReauthPrompt(context, ref, linked);
+  }
 
   @override
   void dispose() {
+    // `dispose()` 안에서는 `ref.read`가 안전하지 않다(Riverpod이 위젯이
+    // 해제되는 동안 사용을 막는다) — `initState`에서 잡아 둔 홀더를 직접
+    // 비운다.
+    _reauthPromptHolder.prompt = null;
     _devNameController.dispose();
     super.dispose();
   }
@@ -47,6 +60,12 @@ class _AccountScreenState extends ConsumerState<AccountScreen> {
       await action();
       if (!mounted) return;
       setState(() => _busy = false);
+    } on ReauthMismatchException catch (e) {
+      if (!mounted) return;
+      setState(() {
+        _busy = false;
+        _errorText = e.message;
+      });
     } catch (e) {
       if (!mounted) return;
       setState(() {
```

`app/lib/features/account/screens/withdraw_screen.dart` — 바꾼다:
```diff
--- a/lib/features/account/screens/withdraw_screen.dart
+++ b/lib/features/account/screens/withdraw_screen.dart
@@ -11,6 +11,7 @@ import '../../../design/tokens/app_typography.dart';
 import '../../../design/widgets/app_button.dart';
 import '../../../design/widgets/app_sheet.dart';
 import '../../../l10n/app_strings.dart';
+import '../state/reauth.dart';
 import '../state/withdraw_controller.dart';
 
 /// 회원 탈퇴 화면. 안내를 확인해야 탈퇴 버튼이 활성화되고, 서버가 추가
@@ -27,6 +28,22 @@ class _WithdrawScreenState extends ConsumerState<WithdrawScreen> {
   bool _busy = false;
   String? _errorText;
   bool _ownershipTransferRequired = false;
+  late final ReauthPromptHolder _reauthPromptHolder;
+
+  @override
+  void initState() {
+    super.initState();
+    _reauthPromptHolder = ref.read(reauthPromptProvider)
+      ..prompt = (linked) => showReauthPrompt(context, ref, linked);
+  }
+
+  @override
+  void dispose() {
+    // `dispose()` 안에서는 `ref.read`가 안전하지 않다 — `initState`에서
+    // 잡아 둔 홀더를 직접 비운다.
+    _reauthPromptHolder.prompt = null;
+    super.dispose();
+  }
 
   Future<void> _withdraw({bool confirmCloseShops = false}) async {
     setState(() {
@@ -56,6 +73,12 @@ class _WithdrawScreenState extends ConsumerState<WithdrawScreen> {
         _errorText = messageFor(e);
         _ownershipTransferRequired = e.code == 'OWNERSHIP_TRANSFER_REQUIRED';
       });
+    } on ReauthMismatchException catch (e) {
+      if (!mounted) return;
+      setState(() {
+        _busy = false;
+        _errorText = e.message;
+      });
     } catch (e) {
       if (!mounted) return;
       setState(() {
```

`app/lib/features/account/state/account_controller.dart` — 바꾼다:
```diff
--- a/lib/features/account/state/account_controller.dart
+++ b/lib/features/account/state/account_controller.dart
@@ -6,6 +6,7 @@ import '../../auth/state/session.dart';
 import '../../auth/state/session_controller.dart';
 import '../../auth/state/social_sign_ins.dart';
 import '../api/account_api.dart';
+import 'reauth.dart';
 
 final accountApiProvider = Provider<AccountApi>(
   (ref) => AccountApi(
@@ -32,18 +33,23 @@ class AccountController extends Notifier<AsyncValue<void>> {
   @override
   AsyncValue<void> build() => const AsyncData(null);
 
+  ReauthCoordinator get _reauth => ref.read(reauthCoordinatorProvider);
+
   /// [signIn]으로 새 로그인 수단을 연결한다. 사용자가 취소하면(`null`)
   /// 요청을 보내지 않는다.
   Future<void> link(SocialSignIn signIn) async {
     final credential = await signIn.signIn();
     if (credential == null) return;
-    await _api.link(credential);
-    await _session.reloadMe();
+    await _linkWithReauth(credential);
   }
 
   /// 개발용 로그인 수단을 이름으로 연결한다.
   Future<void> linkDev(String name) async {
-    await _api.link(SocialCredential(provider: 'dev', token: name));
+    await _linkWithReauth(SocialCredential(provider: 'dev', token: name));
+  }
+
+  Future<void> _linkWithReauth(SocialCredential credential) async {
+    await _reauth.run(() => _api.link(credential));
     await _session.reloadMe();
   }
 
@@ -51,7 +57,7 @@ class AccountController extends Notifier<AsyncValue<void>> {
   /// 이미 저장되었으므로, 그다음에 본인 정보를 다시 불러온다. 구글이었다면
   /// 마지막으로 구글 SDK 연결도 끊는다(베스트 에포트).
   Future<void> unlink(String provider) async {
-    await _api.unlink(provider);
+    await _reauth.run(() => _api.unlink(provider));
     await _session.reloadMe();
     if (provider == 'google') {
       await _disconnectGoogle();
```

`app/lib/features/account/state/reauth.dart`:
```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/error/api_exception.dart';
import '../../../core/proxy/providers.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_button.dart';
import '../../../design/widgets/app_sheet.dart';
import '../../../l10n/app_strings.dart';
import '../../auth/api/social_sign_in.dart';
import '../../auth/state/auth_providers.dart';
import '../../auth/state/session.dart';
import '../../auth/state/session_controller.dart';
import '../../auth/state/social_sign_ins.dart';

/// [linkedProviders](현재 계정에 연결된 로그인 수단)를 받아 사용자가 고른
/// 자격 증명을 돌려준다. 사용자가 시트를 닫기만 하면(취소) `null`.
typedef ReauthPrompt = Future<SocialCredential?> Function(
  List<String> linkedProviders,
);

/// `ReauthCoordinator`가 부를 프롬프트를 담아 두는 자리. 계정/탈퇴 화면이
/// `initState`에서 `prompt`를 채우고 `dispose`에서 비운다 — 화면이 없을 때
/// (이론상 불가능하지만) 프롬프트가 없으면 재인증 없이 원래 오류를 그대로
/// 던진다.
class ReauthPromptHolder {
  ReauthPrompt? prompt;
}

final reauthPromptProvider = Provider<ReauthPromptHolder>(
  (ref) => ReauthPromptHolder(),
);

/// `reauthPromptProvider`에 연결하는 표준 구현. `AppSheet`로 "보안을 위해
/// 다시 로그인해 주세요"를 보여주고, 이 기기에서 쓸 수 있는(`socialSignInsProvider`)
/// 로그인 수단 중 이미 연결된 것만 버튼으로 늘어놓는다(개발 환경의 dev는
/// 이름 입력 필드로).
Future<SocialCredential?> showReauthPrompt(
  BuildContext context,
  WidgetRef ref,
  List<String> linkedProviders,
) {
  final availableSignIns = ref
      .read(socialSignInsProvider)
      .where((signIn) => linkedProviders.contains(signIn.provider))
      .toList();
  final showDev =
      ref.read(appConfigProvider).isDev && linkedProviders.contains('dev');

  return AppSheet.show<SocialCredential?>(
    context,
    builder: (context) => _ReauthSheetContent(
      signIns: availableSignIns,
      showDev: showDev,
    ),
  );
}

class _ReauthSheetContent extends StatefulWidget {
  const _ReauthSheetContent({required this.signIns, required this.showDev});

  final List<SocialSignIn> signIns;
  final bool showDev;

  @override
  State<_ReauthSheetContent> createState() => _ReauthSheetContentState();
}

class _ReauthSheetContentState extends State<_ReauthSheetContent> {
  final _devNameController = TextEditingController();

  @override
  void dispose() {
    _devNameController.dispose();
    super.dispose();
  }

  Future<void> _signInWith(SocialSignIn signIn) async {
    final credential = await signIn.signIn();
    if (mounted) Navigator.of(context).pop(credential);
  }

  void _signInDev() {
    final name = _devNameController.text.trim();
    if (name.isEmpty) return;
    Navigator.of(context).pop(SocialCredential(provider: 'dev', token: name));
  }

  String _labelFor(String provider) => switch (provider) {
        'kakao' => AppStrings.providerKakao,
        'google' => AppStrings.providerGoogle,
        'apple' => AppStrings.providerApple,
        'dev' => AppStrings.providerDev,
        _ => provider,
      };

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          AppStrings.reauthPromptTitle,
          style: AppTypography.body,
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: AppSpacing.lg),
        for (final signIn in widget.signIns) ...[
          SizedBox(
            width: double.infinity,
            child: AppButton(
              label: _labelFor(signIn.provider),
              filled: true,
              onPressed: () => _signInWith(signIn),
            ),
          ),
          const SizedBox(height: AppSpacing.sm),
        ],
        if (widget.showDev) ...[
          TextField(
            controller: _devNameController,
            decoration: const InputDecoration(labelText: AppStrings.devNameLabel),
          ),
          const SizedBox(height: AppSpacing.sm),
          SizedBox(
            width: double.infinity,
            child: AppButton(label: AppStrings.devSignIn, onPressed: _signInDev),
          ),
        ],
      ],
    );
  }
}

/// 재인증 뒤 소셜 로그인이 다른 계정으로 이어졌을 때 던진다. 저장된 토큰은
/// 건드리지 않는다(S6) — 그 세션은 서버에도 베스트 에포트로 로그아웃
/// 통보만 하고 버린다.
class ReauthMismatchException implements Exception {
  const ReauthMismatchException();

  String get message => AppStrings.reauthMismatch;
}

/// `REAUTH_REQUIRED`를 만나면 프롬프트 → 소셜 로그인 → 원 요청 재시도
/// 흐름을 한 번만 수행한다(두 번째 `REAUTH_REQUIRED`는 그대로 던져서
/// 무한 루프를 막는다).
class ReauthCoordinator {
  ReauthCoordinator(this._ref);

  final Ref _ref;

  Future<T> run<T>(Future<T> Function() action) async {
    try {
      return await action();
    } on ApiException catch (e) {
      if (e.code != 'REAUTH_REQUIRED') rethrow;

      final session = _ref.read(sessionControllerProvider).value;
      final me = session is SignedIn ? session.me : null;
      final linkedProviders = me?.identities ?? const <String>[];

      final prompt = _ref.read(reauthPromptProvider).prompt;
      final credential = prompt == null ? null : await prompt(linkedProviders);
      if (credential == null) rethrow;

      final tokens = await _ref.read(authApiProvider).socialLogin(credential);
      if (me != null && tokens.userId != me.id) {
        // 다른 계정의 세션이다 — 여기 머물게 두면 안 되니 베스트 에포트로
        // 로그아웃시키고, 우리 쪽 토큰은 그대로 둔다(S6).
        try {
          await _ref.read(authApiProvider).logout(tokens.refreshToken);
        } catch (_) {
          // 통보 실패는 무시한다 — 어차피 우리 계정과 무관한 세션이다.
        }
        throw const ReauthMismatchException();
      }

      await _ref.read(tokenStoreProvider).save(
            access: tokens.accessToken,
            refresh: tokens.refreshToken,
          );

      return await action();
    }
  }
}

final reauthCoordinatorProvider = Provider<ReauthCoordinator>(
  (ref) => ReauthCoordinator(ref),
);
```

`app/lib/features/account/state/withdraw_controller.dart` — 바꾼다:
```diff
--- a/lib/features/account/state/withdraw_controller.dart
+++ b/lib/features/account/state/withdraw_controller.dart
@@ -3,6 +3,7 @@ import 'package:flutter_riverpod/flutter_riverpod.dart';
 import '../../auth/state/session_controller.dart';
 import '../../auth/state/social_sign_ins.dart';
 import 'account_controller.dart';
+import 'reauth.dart';
 
 /// 탈퇴 화면의 동작을 담당한다. `AccountApi.withdraw`가 204/401을 모두
 /// 성공으로 취급하므로, 이 메서드가 던지지 않고 끝나면 곧 탈퇴가 끝난
@@ -21,9 +22,11 @@ class WithdrawController extends Notifier<AsyncValue<void>> {
     // 탈퇴 뒤에도 SDK 연결을 끊어야 하는데, 그때는 이미 로그아웃 상태라
     // `Me.identities`를 더 읽을 수 없다.
     final identities = ref.read(accountIdentitiesProvider);
-    await ref
-        .read(accountApiProvider)
-        .withdraw(confirmCloseShops: confirmCloseShops);
+    await ref.read(reauthCoordinatorProvider).run(
+          () => ref
+              .read(accountApiProvider)
+              .withdraw(confirmCloseShops: confirmCloseShops),
+        );
     await _session.completeWithdrawal();
     if (identities.contains('google')) {
       await _disconnectGoogle();
```

`app/lib/l10n/app_strings.dart` — 바꾼다:
```diff
--- a/lib/l10n/app_strings.dart
+++ b/lib/l10n/app_strings.dart
@@ -79,6 +79,10 @@ class AppStrings {
   static const unlinkConfirmMessage = '해제하면 다른 모든 기기에서 로그아웃됩니다.';
   static const withdraw = '회원 탈퇴';
 
+  // 재인증
+  static const reauthPromptTitle = '보안을 위해 다시 로그인해 주세요';
+  static const reauthMismatch = '다른 계정입니다. 이 계정에 연결된 로그인 수단으로 다시 로그인해 주세요.';
+
   // 회원 탈퇴
   static const withdrawNoticeIrreversible = '되돌릴 수 없습니다.';
   static const withdrawNoticeShopRecordsStay = '매장의 기록은 매장에 남습니다.';
```

- [ ] **Step 3: 통과와 판별력을 확인한다**

Run: `flutter test && flutter analyze`
Expected: `All tests passed!` (새 테스트 5개 + 탈퇴 화면 테스트에 더한 것), `No issues found!`

`reauth.dart` 에서 `user_id` 를 비교하는 분기를 잠깐 지우고 `flutter test test/features/account/state/reauth_test.dart` 를 돌린다 — `S6 — 다른 계정으로 재로그인하면 저장된 토큰은 그대로고 그 세션은 로그아웃된다` 가 실패해야 한다. 확인한 뒤 되돌린다.

- [ ] **Step 4: 실제 백엔드로 확인한다 (Task 15 가 끝나 있어야 한다)**

`infra/` 에서 `docker compose up -d`, `docker compose restart backend auth`. `app/tool/run_dev.sh` 가 아직 없으면 `flutter run --dart-define=APP_ENV=dev` 로 띄운다. 개발용 로그인 → 앱을 완전히 종료했다가 다시 연다(갱신으로 받은 토큰이 된다) → 설정 → 계정 → 개발용 수단 "해제"를 누르면 수단이 하나라 막혀 있으니, 대신 회원 탈퇴 화면에서 "탈퇴하기" → **재인증 시트가 뜬다** → 같은 이름으로 다시 로그인 → 탈퇴가 이어서 끝나고 로그인 화면이 나온다. 다른 이름을 넣으면 "다른 계정입니다" 문구가 나오고 아무것도 바뀌지 않는다.

- [ ] **Step 5: 커밋**

```bash
git add app/lib app/test
git commit -m "feat(app): 재인증 — REAUTH_REQUIRED 면 한 번 더 로그인하고 한 번만 다시 보낸다"
```

### Task 17: 전체 흐름 확인, 점검표 재확인, 문서

**Files:**
- Create: `app/tool/run_dev.sh`, `_docs/decisions/004-flutter-app-and-reauth.md`
- Modify: `app/CLAUDE.md`, `CLAUDE.md`(저장소 표·명령어), `README.md`, `_docs/harness.md`, `docs/superpowers/specs/2026-09-20-foundation-design.md`(6·8절)

**Interfaces:**
- Consumes: 앞선 모든 작업. 새로 만드는 코드는 없다.
- Produces: 시뮬레이터에서 끝까지 도는 앱과 그 확인 기록, 결정 기록 004.

- [ ] **Step 1: 정적 확인**

Run (`app/` 에서):
```bash
flutter analyze
flutter test
```
Expected: `No issues found!`, `All tests passed!`

점검표 S4(토큰이 로그에 남지 않는다)를 기계로 확인한다:
```bash
cd app
grep -rnE "\bprint\(|debugPrint\(|LogInterceptor" lib && echo "위반" || echo "깨끗함"
grep -rn "package:liquid_glass_widgets" lib | grep -v "^lib/design/bridge/" && echo "위반" || echo "깨끗함"
grep -rnE "webview|WebView" pubspec.yaml lib && echo "위반" || echo "깨끗함"
grep -rn "Hiss Haus\|hisshaus" lib pubspec.yaml ios/Runner/Info.plist android/app/src/main/AndroidManifest.xml && echo "확인 필요" || echo "깨끗함"
```
Expected: 넷 다 `깨끗함`. (`Hiss Haus` 는 테스트 데이터의 매장 이름으로만 쓸 수 있다 — `lib/` 에는 없어야 한다.)

- [ ] **Step 2: 실행 스크립트**

`app/tool/run_dev.sh`:
```bash
#!/usr/bin/env bash
# 개발용 실행. 백엔드는 infra/ 에서 docker compose up -d 로 먼저 띄운다.
# iOS 시뮬레이터는 127.0.0.1, Android 에뮬레이터는 10.0.2.2 로 호스트에 닿는다.
set -euo pipefail
cd "$(dirname "$0")/.."
BASE_URL="${API_BASE_URL:-http://127.0.0.1:8080}"
exec flutter run \
  --dart-define=APP_ENV=dev \
  --dart-define=API_BASE_URL="$BASE_URL" \
  "$@"
```
`chmod +x app/tool/run_dev.sh`. Android 에뮬레이터에서는 `API_BASE_URL=http://10.0.2.2:8080 app/tool/run_dev.sh -d emulator-5554`.

- [ ] **Step 3: 시뮬레이터에서 설계 8.4절의 흐름을 끝까지 돈다**

준비: `infra/` 에서 `docker compose up -d`, `curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8080/health` → `200`. `open -a Simulator` 뒤 `app/tool/run_dev.sh`.

아래를 순서대로 하고, 단계마다 **기대한 화면이 나왔는지**를 보고서에 적는다(스크린샷은 `xcrun simctl io booted screenshot <파일>` — 토큰이나 초대 코드가 찍힌 화면은 남기지 않는다).

1. 개발용 로그인 "사장" → 소속이 없어 초대 코드 입력 화면.
2. 터미널에서 운영자 지정과 매장 개설(앱에는 운영자 화면이 없다):
   ```bash
   cd infra
   docker compose run --rm backend python scripts/grant_operator.py <사장의 user_id>   # user_id 는 GET /v1/me 의 id
   ```
   매장 개설은 `backend/scripts/check_shop_flow.sh` 가 하는 것과 같은 `POST /v1/platform/shops` 호출이다. 응답의 `owner_invite_code` 를 앱에 입력 → 홈.
3. 설정 → 매장 → 초대 코드 만들기 → 코드가 보인다.
4. 로그아웃 → 개발용 로그인 "직원" → 그 코드로 합류 → 홈. 설정에 **관리 메뉴가 없다**(S9).
5. 로그아웃 → "사장" → 멤버 목록에서 직원을 사장으로 바꿨다가 다시 직원으로 → 내보내기.
6. "직원"으로 로그인 → 소속이 없어 초대 코드 입력 화면(내보낸 계정은 즉시 접근 불가).
7. "사장" → 설정 → 계정 → 회원 탈퇴 → "매장도 함께 닫힙니다" 확인 → 로그인 화면. 같은 이름으로 다시 로그인하면 **새 계정**이라 초대 코드 입력 화면이 나온다.
8. 재인증: 로그인한 채 6분을 기다린 뒤(또는 앱을 재시작해 갱신 토큰으로 들어온 뒤) 계정 → 회원 탈퇴 → "보안을 위해 다시 로그인" 안내 → 개발용 로그인을 한 번 더 → 탈퇴가 이어서 끝난다.
9. 백엔드를 내린 채(`docker compose stop gateway`) 앱을 재시작 → 스플래시의 "다시 시도" → `docker compose start gateway` 뒤 다시 시도 → 홈. **로그아웃되지 않았다**(S2).

하나라도 기대와 다르면 고치지 말고 먼저 기록한다: 어느 단계, 무엇이 나왔는지, 서버 응답 코드. 그 다음 원인 작업의 테스트를 먼저 고친다.

- [ ] **Step 4: 홈 셸을 기준 목업과 나란히 놓고 본다**

`.superpowers/brainstorm/67059-1789889527/content/mono-tone.html` 을 브라우저로 열고 시뮬레이터의 홈 화면과 비교한다: 바탕 그라데이션, 큰 세리프 날짜, 기울인 영문 월·요일, 글래스 탭바, 검정 원형 + 버튼. 다른 점을 결정 기록 004 에 적는다(글꼴이 Didot → Bodoni Moda 인 것은 설계에서 정한 차이다).

- [ ] **Step 5: 문서**

`_docs/decisions/004-flutter-app-and-reauth.md` — `001`~`003` 의 문체를 따른다. 절:
- **무엇을 만들었나** (앱 골격, 화면 흐름, 재인증)
- **설계와 다르게 가거나 새로 정한 것**: 재인증(최근 로그인 확인, 300초, 해제는 `auth_time` 을 물려준다) / 문구는 상수 클래스(`gen-l10n` 미도입) / 테스트와 "투명도 줄이기"에서는 불투명 면 / Flutter 3.44 에는 "투명도 줄이기" 신호가 없어 고대비 설정으로 근사한다 / Apple 버튼은 iOS 만 / 웹뷰 금지(사용자 지시) / 갱신 실패 시 502·503·504 는 토큰 유지, 그 밖은 이 기기만 로그아웃 / Riverpod 자동 재시도 끔 / `crypto` 를 열 번째 의존성으로(Apple nonce 의 SHA-256) / 카카오·구글·Apple 의 네이티브 설정은 키 등록 뒤(`app/NATIVE-SETUP.md`) / `flutter_animate` 는 설치만 되어 있고 쓰는 곳이 없다(움직임은 `Pressable` 의 스프링으로 충분했다 — ③에서도 쓰지 않으면 뺀다)
- **검토에서 고친 것** (작업별 검토와 최종 검토가 잡은 것을 실행 중에 채운다)
- **남는 것 — 알고 미룬다**: 로그인 직후 300초 안에 훔친 토큰은 여전히 통한다 / 카카오·구글·Apple 실기기 확인은 키 등록 뒤(설계 8.3) / 글꼴 용량(Pretendard 가변 6.7MB + 마루 부리 3.3MB) — 출시 전 서브셋 검토 / 오프라인 캐시 없음 / 다국어 없음 / 탈퇴의 401 은 "완료"로 보지만, 만료된 토큰 + 다른 기기에서 폐기된 세션이 겹치면 계정이 남아 있을 수 있다(다시 로그인하면 보인다) / SDK 어댑터(카카오·구글·Apple)는 단위 테스트가 없다 — 실기기 확인이 유일한 검증이다
- **다음 서브 프로젝트(② 고객·반려견)로 넘기는 것**

`app/CLAUDE.md` 를 최종 상태로 맞춘다(폴더 규칙, 세 층 규칙, 글래스 import 경계, 웹뷰 금지, 토큰 로그 금지, 갱신 규칙, 명령어). 루트 `CLAUDE.md` 의 저장소 표에서 앱 줄의 "위치"가 `app/` 인지 확인하고 명령어 절에 `app/tool/run_dev.sh` 와 `flutter analyze`·`flutter test` 를 더한다. `_docs/harness.md` 에 앱 검증 명령을 더한다. 설계 문서 6.1절의 의존 패키지·폴더가 실제와 같은지, 8.2절 표가 실제 테스트와 맞는지 확인하고 다르면 고친다.

- [ ] **Step 6: 커밋**

```bash
git add app/tool _docs docs CLAUDE.md README.md app/CLAUDE.md
git commit -m "docs: 앱 골격과 재인증의 결정 기록 004, 실행 스크립트와 검증 절차를 남긴다"
```
