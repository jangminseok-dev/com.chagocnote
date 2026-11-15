# 014 — 전자 동의서·문진표 (⑪)

설계 `docs/superpowers/specs/2026-11-16-consent-intake-design.md`, 여섯 묶음의 공통 기준 `docs/superpowers/specs/2026-11-16-next-designs-common.md`. 보호자가 로그인 없이 웹에서 적어 보내는 서류다. ⑪ 은 셋으로 나눠 만든다(사용자 승인 2026-11-16) — **⑪-A 동의서** → ⑪-B 한 번에 보내기·서류 설정 → ⑪-C 문진표.

사용자의 기준(2026-11-16): 자동화할 수 있는 것은 자동화한다 · 경쟁사보다 압도적으로 편해야 한다 · 그렇다고 핵심 기능·설명·바꿀 길을 빼지 않는다 · 기본값은 업계에서 흔한 방식으로 두고 매장이 자기 가게에 맞게 고른다 · 가족이 함께 예약하면 서명 한 번으로 여러 아이의 동의를 받는다. 문안·항목·기준값·구조는 내가 정했다.

## ⑪-A 백엔드에서 정한 것 (2026-11-16)

계획 `docs/superpowers/plans/2026-11-16-consent-11a-backend.md`. 규칙은 `backend/apps/customer/CLAUDE.md`.

1. **알림장의 공개 도구 넷을 `core/`·`hub/` 로 올렸다.** 토큰(`core/link_token.py`), 접속 주소(`core/public_client.py`), 횟수 제한(`hub` 의 `PublicLimiterPort` + `core/public_redis_limiter.py`), `public_context`(`hub/app/dtos/shop_context.py`). 알림장의 동작은 그대로다 — 이미 나간 링크의 토큰이 글자 하나 다르지 않다는 것을 테스트가 고정한다.
2. **서류 토큰은 알림장 토큰과 서로의 경로에서 읽히지 않는다.** 같은 키(`REPORT_LINK_KEY`)로 서명하되 서명 대상 앞에 `form:` 을 붙인다. 새 비밀값이 없다. 헤더는 `X-Form-Token`.
3. **`public_context` 가 처음으로 쓴다.** 로그인 없는 경로가 고객 스포크의 표를 쓰는 첫 사례다 — 쓰는 표를 루트 `CLAUDE.md` 에 적었다(`customer_forms`·`consent_signatures` 와 그 아래 표, `pets` 의 동의 칸 셋).
4. **문안은 열 때 조립하고, 낼 때 지문을 다시 견준다.** 지문은 아이마다 이름·남은 토막·그 글의 출처와 판·지병 이름 목록의 해시다. 읽은 뒤 지병이 하나 더해져도 409 이고 서명이 저장되지 않는다.
5. **서명은 읽은 토막과 그때 보인 사실의 사본을 남긴다.** 그래서 뒤에 노령이 되거나 지병이 늘면 **바뀐 토막만** 다시 받는다. 부분 서명은 받은 날을 옮기지 않는다 — 기한은 처음 전체를 받은 날부터 365일이다.
6. **판정은 지금처럼 `visit` 이 방문의 날로 한다.** `customer` 는 사실만 준다 — 허브 DTO `PetCareFact` 에 `consent_cover`(서명이 덮는 것)와 `consent_form_sent_on`(살아 있는 링크를 보낸 날). 확인할 것의 `consent` 에 상태 `partial` 과 `parts`, `form_sent_on` 이 더해졌다(값이 있을 때만 칸이 있다).
7. **서명으로 받은 동의는 지병이 늘어도 받은 날을 지우지 않는다.** 손으로 적은 동의(③-B 의 [받았어요])는 지금처럼 지운다.
8. **아이 하나에 살아 있는 동의서 요청은 하나다.** 요청이 아이 여럿을 담아 부분 유일 색인으로 쓸 수 없다 — 발급이 고객 행을 잠근 안에서 지킨다. 같은 아이들에게 다시 보내면 같은 링크(200), 새로 만들면 201.
9. **서명을 받으면 그 아이는 살아 있는 다른 링크에서 빠진다.** 아이가 남지 않은 링크는 끊긴다 — 같은 것을 두 번 서명받지 않는다.
10. **서명 그림은 DB 에 둔다**(64KB 이하의 PNG 한 장). 로그인 없는 경로에 업로드 발급을 열지 않는다. 서버는 그림을 풀지 않고 머리·폭·높이·크기만 본다.
11. **기준값은 `ConsentPolicy` 로 받는다**(노령 10살·기한 365일·링크 14일). 지금은 기본값뿐이고 `customer/dependencies/customer_wiring.consent_policy()` 가 준다 — 매장이 바꾼 값은 ⑪-B 가 여기서 읽는다. 다만 **`visit` 의 판정은 아직 자기 상수(10·365)를 쓴다** — ⑪-B 가 매장 설정을 읽게 할 때 두 곳을 함께 바꿔야 한다.

## 실행하면서 정한 것 (Ruling)

- **손으로 적은 동의는 노령이 돼도 다시 묻지 않는다.** 설계 3.3 은 "받은 날에는 노령이 아니었으면 전체를 다시"라 했고 F14 는 "손 표시의 규칙은 그대로"라 했다 — F14 를 따랐다(③-B 의 동작을 바꾸지 않는다). 손 표시 뒤 10살이 된 아이의 동의를 놓치는 것은 지금도 같다.
- **확인할 것의 `form_sent_on`·`parts` 는 값이 있을 때만 싣는다.** ③-B 의 테스트가 `detail` 을 통째로 견준다.
- **손 표시는 살아 있는 링크를 끊지 않는다.** 그 링크를 열면 "보냈어요"로 읽히고 내면 409 `CONSENT_UP_TO_DATE` 다. 보낸 서류 목록에는 기간까지 남는다.
- **횟수 제한의 오류 code 는 알림장과 같은 `TOO_MANY_ATTEMPTS`**, 공개 응답의 헤더도 알림장과 같은 둘이다(`Referrer-Policy` 는 웹이 붙인다).
- **익명화는 이미 낸 링크도 닫는다.** 흐름 스크립트가 잡았다 — 낸 링크가 익명화 뒤에도 "보냈어요"로 열렸다. 개인정보는 없었지만 알림장과 같게 410 으로 맞췄다.
- 라우터별 스텁 테스트는 쓰지 않고 실제 배선 통합 테스트로 덮었다. 통합 테스트 일부는 구현 뒤에 처음 돌렸고, 대신 변이 33개로 판별력을 확인했다(살아남은 둘은 테스트를 더해 잡았고, 하나는 같은 결과인 변이다).

## ⑪-A 의 API 계약 (웹·앱이 기댄다)

매장(`/v1/shops/{shop_id}/…`):

- `POST consent-forms {pet_ids}` → `{form_id, url, expires_on, sent_on}` (201 새로 / 200 같은 링크). `customer:write`.
- `GET forms` → `{items: [{form_id, kind, customer: {customer_id, name}, pets: [{pet_id, name}], sent_on, expires_on, url}]}` · `DELETE forms/{form_id}` → 204.
- `GET consent-document?pet_ids=1&pet_ids=2` → `{pets: [{pet_id, name, conditions, parts}], texts: {part: {body}}, previous_consent_on, doc_digest}` · `POST consent-signatures {pet_ids, doc_digest, signer_name, signature_png(base64)}` → 201 `{signature_id}`.
- `GET pets/{pet_id}/consent-signatures` · `GET consent-signatures/{id}` · `GET consent-signatures/{id}/image`(`image/png`).
- 반려동물 상세의 `pet.grooming_consent_via`: `signature`·`manual`·`null`.
- 오류: 404 `FORM_NOT_FOUND`·`SIGNATURE_NOT_FOUND` · 409 `CONSENT_DOCUMENT_CHANGED`·`CONSENT_UP_TO_DATE` · 410 `FORM_CLOSED` · 429 `TOO_MANY_ATTEMPTS`.

공개(로그인 없음, 헤더 `X-Form-Token`):

- `GET /v1/public/form` → 열림 `{kind, state: "open", shop: {name}, previous_consent_on, pets: [{name, conditions, parts}], texts, doc_digest}` / 냄 `{kind, state: "submitted", shop: {name}, submitted_on}`.
- `POST /v1/public/form/consent {doc_digest, signer_name, signature_png}` → 204 / 409 / 410 / 404 / 422 / 429(10분에 10번).

## 받아들인 한계

- **본인 인증이 없다.** 서명한 사람이 누구인지 증명하지 않는다. 화면·문서에서 "법적 효력"을 말하지 않는다. 기본 문안은 법률 검토를 받지 않았다.
- 링크를 받은 사람은 아이 이름과 지병의 **이름**을 본다(메모는 싣지 않는다).
- 동의의 '오늘'은 매장 쪽 경로가 `seoul_today`, 공개 경로가 매장 시간대다 — 한국 밖의 매장에서는 하루가 어긋날 수 있다(스포크의 지금 규칙과 같다).
