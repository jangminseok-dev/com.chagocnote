# 010 — 보호자 회원(⑦)에서 내린 결정

설계: `docs/superpowers/specs/2026-11-13-guardian-design.md`. 이 기록은 계획마다 절을 더한다(⑦-1 백엔드 → ⑦-2 웹 → ⑦-3 앱).

## 사용자와 정한 것 (2026-11-13)

| 주제 | 결정 |
|---|---|
| 어디서 보나 | 웹 먼저(chagocnote.com). 보호자 앱은 만들지 않는다 |
| 본인 확인 | 받은 알림장 링크로 한다. 업계 표준(MoeGo·Gingr — 매장에 등록된 전화번호 매칭)과 다르다는 것을 조사해 알렸고, 문자 인증(건당 비용)·카카오 전화번호(사업자 심사)를 지금 쓰지 않기로 해 링크 방식을 골랐다. 나중에 덧붙일 수 있게 `verified_by` 를 남긴다 |
| 보이는 범위 | 매장이 알림장을 보낸 방문만. 링크 기간이 지난 것도 보이고 매장이 끊은 것은 안 보인다. 항목은 매장의 알림장 설정을 따른다. 내부 메모는 절대 보이지 않는다 |
| 연결 | 고객 카드 하나에 계정 하나. 매장이 보고 끊을 수 있다 |
| 웹 세션 | **30분, 연장 없음.** 리프레시 토큰 재사용이 감지되면 그 계정의 모든 세션(매장 앱 포함)이 끊기는데 웹은 탭 둘·뒤로 가기로 갱신이 겹치기 쉽다 — 웹에는 리프레시 토큰을 주지 않는다(내 권고는 15분, 사용자가 30분으로 정했다) |
| 비용 | 기능과 로컬 테스트까지만. 실제 카카오·애플 웹 로그인 연결·배포는 사용자가 따로 말할 때 |
| 미룬 것 | 보호자 수신 설정·차단(⑥ 설계가 ⑦로 미뤘던 것)은 다음 차례 |

## ⑦-1 백엔드에서 정한 것

계획: `docs/superpowers/plans/2026-11-13-guardian-7-1-backend.md`.

### 구조

- 새 스포크 `guardian` 이 연결(`guardian_links`, 마이그레이션 0014)과 잇기·끊기를 소유한다. 알림장 읽기는 `visit` 이 소유한 채 보호자용 경로 셋을 더했다(`guardian_reports_router.py`).
- 허브 포트 셋: `ReportLinkPort`(구현 visit — 토큰 → 매장·고객·열림), `GuardianAccessPort`(구현 guardian — 보호자 가드), `GuardianLifecyclePort`(구현 guardian — 탈퇴·익명화가 부른다). 허브 DTO `ReportLinkTarget`·`GuardianContext`, 허브 오류 `GuardianAccessDeniedError`(404 `GUARDIAN_LINK_NOT_FOUND`).
- 보호자 가드 `core/guardian_guard.get_guardian_context` — `core/shop_guard` 의 짝.
- **`guardian` 은 `ShopContext` 를 만들지 않고 고객·반려동물을 읽지 않는다.** 보호자용 읽기(visit)는 `visit/app/services/public_context.py` 를 그대로 쓴다(`guardian_scope`) — 가드 없이 `ShopContext` 를 만드는 곳은 여전히 둘이다.
- `GuardianLinkRepository` 는 `ShopContext` 를 받지 않는다(범위가 계정이다).

### 이 계획에서 정한 것

1. 웹 세션 표시는 소셜 로그인 본문의 `session: "web"`. 그때 `refresh_token` 은 null, `expires_in` 은 1800(`WEB_ACCESS_TOKEN_TTL_SECONDS`). 표시가 없으면 매장 앱의 로그인 그대로다(900초 + 리프레시). 웹 세션 토큰은 보통의 액세스 토큰이라 같은 계정의 다른 API 도 30분 동안 듣는다(같은 사람이다). **다만 로그인 시각(`auth_time`)을 찍지 않아 '최근 로그인'이 필요한 일(탈퇴·수단 연결·해제)은 하지 못한다**(403 `REAUTH_REQUIRED`) — 수단 해제가 30일짜리 토큰 쌍을 내주는 길로 리프레시 토큰이 웹에 나가지 않게(최종 검토). 계정을 바꾸는 일은 매장 앱에서 한다.
2. 잇기 횟수 제한은 계정당 시간당 10회(Redis, 닿지 못하면 통과). 맞든 틀리든 센다.
3. 유저 행을 잠갔더니 탈퇴·정지된 계정이면 401 `UNAUTHENTICATED`(`GuardianAccountInactiveError`).
4. 지난 알림장 목록의 쪽 나눔은 `cursor`(마지막 줄의 방문 시작 시각·방문 ID 를 감싼 글자), 20개씩, `{items, next_cursor}`. 깨진 글자는 422.
5. `report_id` 는 `visit_reports.id` 다. 그 연결의 고객 것이 아니면 404 `REPORT_NOT_FOUND`.
6. 아이들(`…/pets`)은 **알림장을 받은 적 있는 아이만** — 매장에 등록만 된 아이의 이름은 드러나지 않는다. 무지개다리를 건넌 아이도 넣는다. 보호자만의 방문의 알림장은 목록에 `pet_id: null` 로 있고 아이들에는 없다.
7. 한 장의 응답은 공개 알림장의 스키마(`PublicReportSchema`) 그대로이고 `expires_at` 은 늘 null 이다. 열람 신호를 찍지 않는다. 목록·한 장 응답에 `Cache-Control: private, no-store`.
8. 이은 날(`linked_at`)은 매장 시간대로 준다.
9. 자기소개 경로는 `/v1/me/guardian/myself`(로그인 필요) — 로그인 없는 경로를 늘리지 않았다.
10. 매장이 정지·폐업이면 그 연결은 목록에서 빠지고 읽기는 빈 목록·404 다.
11. 익명화는 연결을 끝낸다(`anonymized`) — guardian 이 읽을 때마다 고객을 확인하는 대신(guardian 은 고객을 읽을 컨텍스트가 없다) customer 의 삭제가 허브 포트를 부른다.

### 알려진 동작 — 막지 않기로 했다

- **기간이 지난 알림장 한 장만 숨기는 길은 없다.** [링크 끊기]는 열려 있는 링크에만 있다. 매장이 지난 알림장 하나를 감추려면 그 방문에서 알림장을 다시 보낸 뒤 끊거나 보호자 연결을 끊는다. 기능을 넣기 전에 기간이 지난 알림장들도 이으면 함께 보인다(그것이 "지난 기록 다시 보기"다).
- 매장이 기간 지난 알림장을 다시 보내면 옛 줄은 닫히고(`close_expired`) 새 줄 한 장만 보인다 — `report_id` 가 바뀐다.
- 탈퇴한 계정의 남은 웹 토큰은 인증 단계에서 막히거나(401) 연결이 끝나 막힌다(404) — 어느 쪽이든 읽히지 않는다.
- 익명화와 잇기가 겹치면(잇기가 열린 링크를 확인한 직후 익명화가 커밋) 익명화된 카드에 살아 있는 연결 한 줄이 남을 수 있다. 알림장이 모두 끊겨 목록·아이들·한 장은 비어 있고 새는 것은 없다 — 보호자 목록에 매장 이름만 있는 빈 연결이 남는다(보호자가 끊을 수 있다).
- 잇기 횟수는 이미 이어진 계정의 200 응답도 센다 — 한 시간에 열한 번째 누르면 이미 이어진 보호자도 429 를 받는다(⑦-2 웹은 429 를 받아도 `/me` 로 보낸다).
- 유저 행을 잠근 뒤 다시 봤을 때 정지된 계정도 401 `UNAUTHENTICATED` 다(가드는 403 `ACCOUNT_SUSPENDED`) — 경합 창에서만 보이는 차이다.
- 연결 목록은 연결마다 매장 공개 정보를 한 번씩 읽는다(연결 수가 적다).
- 웹 세션 토큰에는 폐기 수단이 없다(리프레시 세대와 무관하다). 웹 로그아웃은 쿠키를 지우는 것이고 토큰은 30분 뒤 스스로 끝난다.

### 막지 못하고 감수하는 것

1. **전달받은 링크로 남이 이을 수 있다**(G1). 카드당 연결 하나, 열린 링크로만, 매장이 "연결됨"을 보고 끊는다.
2. **매장 직원이 [다시 공유]로 얻은 링크로 자기 계정에 이을 수 있다**(G13). 매장 안에서는 이미 다 보이는 사람이지만 매장을 떠난 뒤에도 볼 수 있다 — 매장이 끊는다.
3. 보호자가 이미 내려받은 사진은 끊어도 회수할 수 없다.

### 남는 것 — 알고 미룬다

- 실제 카카오·애플 웹 로그인 연결, 배포(사용자가 풀 때).
- 전화번호 확인(`verified_by` 값 추가), 웹 로그인 유지(인증에서 웹 세션 분리).
- 보호자 수신 설정·차단 플래그.
- 보호자 읽기 경로가 반드시 `get_guardian_context` 를 거친다는 구조 테스트(`route_inspection` 의 매장 경로 짝)는 아직 없다 — 보호자 읽기를 더할 때 함께 둔다.
- 0014 의 `downgrade` 는 돌려 보지 않았다.

### ⑦-2 웹·⑦-3 앱이 기댈 API 계약

**웹 세션 로그인**(인증 프로세스 — 게이트웨이 또는 `AUTH_BASE_URL`)

`POST /v1/auth/social` `{"provider": "dev" | "kakao" | "apple" | "google", "token": str, "session": "web"}` → 200 `{access_token, refresh_token: null, token_type: "Bearer", expires_in: 1800, user_id, is_new_user}`. `session` 은 `"web"` 만 받는다(다른 값 422). 개발용 `dev` 제공자는 인증 프로세스가 `APP_ENV=dev` 일 때만 있다(`token` = 로그인할 이름).

**보호자**(전부 `Authorization: Bearer <액세스 토큰>`, 접두 `/v1/me/guardian`, 오류 본문은 `{code, message}`)

| 메서드·경로 | 요청 | 성공 | 오류 |
|---|---|---|---|
| POST `/links` | 헤더 `X-Report-Token` (본문 없음) | 201 `{"link_id": int}` · 이미 내 연결이면 200 같은 모양 | 404 `REPORT_NOT_FOUND`(헤더 없음·우리 토큰 아님) · 410 `REPORT_CLOSED` · 409 `GUARDIAN_ALREADY_LINKED` · 429 `GUARDIAN_RATE_LIMITED` · 401 |
| GET `/links` | — | 200 `{"items": [{"link_id", "shop_name", "linked_at"}]}` 이은 순 | 401 |
| DELETE `/links/{link_id}` | — | 204 | 404 `GUARDIAN_LINK_NOT_FOUND` · 422 |
| GET `/links/{link_id}/pets` | — | 200 `{"items": [{"pet_id", "name"}]}` | 404 `GUARDIAN_LINK_NOT_FOUND` |
| GET `/links/{link_id}/reports` | 질의 `pet_id`(선택), `cursor`(선택) | 200 `{"items": [{"report_id", "visit_date": "YYYY-MM-DD", "pet_id": int\|null, "pet_name": str\|null, "cover": {"url","width","height"}\|null, "media_count": int}], "next_cursor": str\|null}` 최신순 20개 | 404 `GUARDIAN_LINK_NOT_FOUND` · 422(`cursor`·`pet_id`) |
| GET `/links/{link_id}/reports/{report_id}` | — | 200 공개 알림장과 같은 본문(008 의 `GET /v1/public/report`), `expires_at: null` | 404 `GUARDIAN_LINK_NOT_FOUND` · 404 `REPORT_NOT_FOUND` · 422 |

- `cover.url` 과 한 장의 미디어 주소는 서명 주소다(짧게 산다) — 저장하지 않는다.
- 끈 항목은 칸이 없고(`menus`·`total_amount`·`weight_kg`·`shop`), 켰지만 값이 없으면 null 이다(공개 알림장과 같다).
- 30분이 지난 토큰은 401 이다 — 웹은 다시 로그인시킨다. 정지된 계정은 모든 경로에서 403 `ACCOUNT_SUSPENDED`.
- `pets[].name` 은 `str | null` 이다. `…/pets`·`…/reports` 의 `link_id` 가 범위 밖 숫자면 422.
- `GET /v1/me/guardian/myself`(로그인 필요)는 스포크의 자기소개다 — 웹은 쓰지 않는다.
- **웹 서버는 `/v1/auth/social` 외의 `/v1/auth/*` 를 부르지 않는다**(탈퇴·수단 연결·해제는 웹 세션으로 되지 않는다).

**매장**(접두 `/v1/shops/{shop_id}`)

| 메서드·경로 | 권한 | 성공 | 오류 |
|---|---|---|---|
| GET `/customers/{customer_id}/guardian-link` | 소속 | 200 `{"linked": bool, "linked_at": datetime\|null}`(매장 시간대) | 403 `NOT_A_MEMBER` · 422 |
| DELETE `/customers/{customer_id}/guardian-link` | `customer:write` | 204 | 404 `GUARDIAN_LINK_NOT_FOUND`(연결 없음) · 403 `PERMISSION_DENIED` |

매장이 정지·폐업이면 403 `SHOP_SUSPENDED`·`SHOP_CLOSED`(기존 매장 가드). 보호자가 누구인지는 어느 응답에도 없다.

### 최종 검토(2026-11-13)가 찾은 것과 처리

- Important — 쪽 나눔(`before`)·`pet_id` 거르기·보호자만의 방문이 스텁으로만 증명되고 실제 PostgreSQL 에서 실행된 적이 없었다. **메웠다**: pg 저장소 테스트 넷(세 쪽 넘기기, 같은 시각의 두 방문이 쪽 경계에 걸림, 아이 거르기와 보호자만의 방문, 끊음·기록 없음·다른 고객·다른 매장). SQL 은 그대로 통과했다.
- 조작한 쪽 표시(UTC 로 바꾸면 범위를 넘는 시각)가 DB 바인딩까지 가 500 이 될 수 있었다. **고쳤다**: 디코드에서 UTC 로 바꾸고 넘치면 422.
- 웹 세션 토큰이 '최근 로그인'을 통과해 탈퇴·수단 해제가 됐다(수단 해제는 30일 리프레시 쌍을 내준다 — 실제로 탈퇴가 되는 것을 테스트로 확인했다). **고쳤다**: 웹 세션은 `auth_time` 을 찍지 않는다.
- 쓰지 않는 import·의존성 정리.
- 미룬 것은 위 "알려진 동작"·"남는 것"에 적었다(익명화와 잇기의 경합, 이미 이은 계정의 429, 경합 창의 401, 구조 테스트).

### 흐름 확인

2026-11-13 — 단위 2032(기존 1941 + 새 91) · 통합 541(기존 507 + 새 34) · import-linter 6 kept(스포크 여덟) · 라우트 표 80 → 89줄(늘어난 경로는 `/v1/me/guardian/…` 일곱과 `…/guardian-link` 둘, 없어지거나 바뀐 줄 없음) · 로그인 없는 경로 목록 불변 · 개발 DB 에 0014 올림. `backend/scripts/check_guardian_flow.sh` 를 개발 스택(게이트웨이 → 인증·API 두 프로세스)에서 돌려 일곱 단계·확인 30줄 모두 통과했다. 판별력: "한 장에 내부 메모가 없다"의 기대를 뒤집으면 그 줄에서 멈춘다. 기존 `check_report_flow.sh`(34줄)·`check_notification_flow.sh`(53줄)도 그대로 통과했다. 변이 — 내 연결 판정 제거, 기록 확인 제거, 끊은 알림장 조건 제거, 고객 조건 제거 — 각각 해당 테스트가 떨어지는 것을 확인했다.
