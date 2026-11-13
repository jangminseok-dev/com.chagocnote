# guardian — 보호자 계정과 매장의 고객 카드를 잇는 연결

소유 데이터: `guardian_links`(보호자 계정 ↔ 고객 카드, 끝난 줄도 남는다), Redis 의 잇기 횟수 제한. 설계는 `docs/superpowers/specs/2026-11-13-guardian-design.md`, 결정은 `_docs/decisions/010-guardian.md`.

- **보호자는 매장의 멤버가 아니다.** 범위는 로그인한 계정(user_id)이고 경로는 `/v1/me/guardian/…` 다. 그래서 `GuardianLinkRepository` 는 `ShopContext` 를 받지 않는다 — `PublicReportRepository`·`NotificationQueueRepository` 와 같은 예외다. 매장 쪽 유스케이스(`…/customers/{customer_id}/guardian-link`)는 가드가 준 `ShopContext` 의 `shop_id` 를 넘긴다.
- **이 스포크는 `ShopContext` 를 만들지 않고 고객·반려동물을 읽지 않는다.** 연결 목록은 매장 이름(`ShopProfilePort.public_profile` — 매장 ID 만 받는다)과 이은 날만 준다. 아이들과 지난 알림장은 `visit` 이 같은 접두 아래에서 준다(`visit/adapter/inbound/api/v1/guardian_reports_router.py`).
- **잇기는 받은 알림장 링크로 한다**(`claim_guardian_link`). 링크는 매장이 그 보호자의 번호로 보낸 것이라 링크를 가진 것이 본인 확인을 대신한다 — 업계 표준(매장에 등록된 전화번호 매칭)과 다르고, 그래서 `verified_by`(`report_link`)를 남긴다. 전화번호 확인을 더하면 값이 는다.
  - 순서: 횟수 제한(계정당 시간당 10회, Redis 에 닿지 못하면 통과) → 유저 행 잠금(`ActiveUserGuardPort.lock_active` — 탈퇴와 겹치면 기다리고, 탈퇴·정지된 계정은 401) → `ReportLinkPort.resolve`(visit) → 없으면 404 `REPORT_NOT_FOUND`, 닫혔으면 410 `REPORT_CLOSED` → 그 카드의 살아 있는 연결이 내 것이면 200, 남의 것이면 409 `GUARDIAN_ALREADY_LINKED` → 없으면 만든다(201).
  - **고객 카드 하나에 살아 있는 연결은 하나다**(부분 유일 색인 `uq_guardian_links_live(shop_id, customer_id) WHERE ended_at IS NULL`, 세이브포인트 — 동시에 온 둘째는 409).
  - 알림장 토큰은 헤더 `X-Report-Token` 으로만 받고 로그·오류 본문·DTO 의 repr 에 남기지 않는다.
- **연결이 끝나는 네 가지**(`ended_by`): 보호자가 끊음(`guardian`), 매장이 끊음(`shop`, `customer:write`), 계정 탈퇴(`withdrawn` — auth 의 탈퇴가 `GuardianLifecyclePort.end_for_user` 를 부른다, 인증 프로세스), 고객 익명화(`anonymized` — customer 의 삭제가 `end_for_customer` 를 부른다). 끝난 줄은 지우지 않는다. 끊은 뒤 열린 링크로 다시 이으면 새 줄이다.
- 잠금 순서의 끝이다 — 유저 행 → … → **보호자 연결 행**, 고객 행 → **보호자 연결 행**. 탈퇴와 익명화는 부르는 쪽이 이미 잠근 트랜잭션 안에서 돈다.
- **매장에는 보호자가 누구인지 주지 않는다.** 매장용 응답은 `{linked, linked_at}` 뿐이다(기반 설계 5.1 — 매장은 고객이 다른 매장의 사장인지 알 수 없다). 다른 매장의 고객 번호를 넣으면 연결이 없는 것으로 보인다.
- **보호자 가드**는 `core/guardian_guard.get_guardian_context` 다 — 경로의 `link_id` 가 그 계정의 살아 있는 연결인지 매 요청마다 본다(`GuardianAccessPort`, 이 스포크가 구현). 아니면 404 `GUARDIAN_LINK_NOT_FOUND`(없는 연결·남의 연결·끝난 연결을 구분하지 않는다). `core/shop_guard` 의 보호자 쪽 짝이고, 보호자용 읽기를 가진 스포크(visit)가 쓴다.
- 정지·폐업한 매장의 연결은 목록에서 빠진다. 이은 날(`linked_at`)은 매장 시간대로 준다.
- 전화번호·이름을 저장하지 않는다.
- 스텁(`tests/helpers/fakes.py`)은 포트 ABC 를 상속한다(`tests/test_fakes_are_ports.py`). 통합 테스트의 첫 줄은 테넌트 격리다(남의 연결 → 404) — `tests/integration/test_guardian_wiring.py`.
