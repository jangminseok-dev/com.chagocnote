# visit — 방문(예약부터 완료까지), 미용 기록, 매장 일정, 메뉴표

소유 데이터: `visits`, `visit_menus`, `visit_records`, `visit_record_items`, `visit_record_media`, `visit_reports`, `visit_shop_settings`(일정 설정과 알림장 설정 칸), `visit_weekly_closures`, `visit_closed_dates`, `service_menus`, Redis의 공개 알림장 조회 횟수.

- 방문 하나는 반려동물 한 마리의 방문이다. `pet_id`가 NULL 이면 보호자만의 방문이다. 두 마리를 한 번에 잡으면 방문이 둘이고, 같은 보호자 + 같은 시작 시각이 가족 묶음이다(저장하지 않고 계산한다).
- `visits`의 `shop_id`·`customer_id`·`pet_id`는 다른 스포크의 ID 라 외래 키가 없다. 이름·품종 같은 보호자·반려동물 정보는 복사하지 않고 허브 포트 `CustomerDirectoryPort.briefs`로 읽는다(`app/services/visit_reader.py`).
- 상태는 `domain/state/`(State 패턴)가 정한다: 예약됨 → (미용 중) → 완료 / 취소(사유 필수) / 노쇼, 되돌리기는 예약됨으로. 상태가 원본이고 시각·사유 칸은 그 상태일 때만 있다(CHECK). **상태 이름과 성질(살아 있음·마릿수·시작 시각)의 단일 원천은 `domain/state/visit_status.py`의 표다** — `ACTIVE_STATUSES`·`COUNTED_STATUSES`·ORM CHECK·부분 색인·하루 집계 칸이 거기서 파생한다. 상태를 더하면 표에 한 줄, `visit_state.py`에 상태 클래스 하나, `DayCountsView`에 칸 하나, 그리고 새 마이그레이션이다(`test_schema_drift`는 CHECK·부분 색인을 보지 않는다 — `tests/integration/test_visit_status_schema.py`가 실제 DB 와 표를 대조해 알려 준다).
- 행동(시작·완료·취소·노쇼·되돌리기)은 `visit_state.ACTIONS`와 바탕 상태 클래스의 같은 이름 메서드가 정한다. `transition()`은 행동 이름으로 메서드를 찾으므로 행동을 더할 때 if 체인을 늘리지 않는다. 시간을 다시 차지하는 행동(`SLOT_RECLAIMING_ACTIONS`)만 가족 확인에 반려동물을 넘긴다(`pets_to_confirm`). 방문의 사실이 바뀐 뒤 customer 에 알리는 후속 처리는 `app/services/completion_effects.py` 한 곳이다 — 전이는 최근 방문 갱신(`apply_completion_effects`)만, 기록 쓰기는 몸무게 동기화(`sync_pet_weight`)만 부른다.
- **방문을 쓰는 유스케이스는 맨 앞에서 고객 행을 잠근다** — `CustomerDirectoryPort.lock_family`(customer 구현) → 방문 행(ID 오름차순 `FOR UPDATE`) → 다시 읽기. `app/services/visit_locking.py`가 이 순서를 한 곳에 둔다. 외래 키가 없어 이 잠금이 없으면 익명화·무지개다리·반려동물 삭제와 겹친다.
- `visits` 표의 리포지토리는 포트 여섯으로 나뉜다(`app/ports/output/visit_*_repository.py`): 찾기·잠금(`VisitLookupRepository`), 쓰기(`VisitWriteRepository`, 찾기·잠금을 상속), 이력(`VisitHistoryRepository` — 완료 때 같은 아이의 앞선 완료 방문 시작 시각을 주는 `latest_completed_start_excluding` 포함), 원장(`VisitLedgerRepository`), 게시판(`VisitBoardRepository`), 피드(`VisitFeedRepository` — 완료 시각 순). 구현은 `VisitPgRepository` 하나가 다 상속하고, 유스케이스는 자기가 부르는 포트만 생성자로 받는다(같은 인스턴스를 인자마다 넘긴다). 포트에 메서드를 더할 때는 그 축에 넣고, 새 축이면 포트를 새로 만든다.
- customer 는 반대 방향 허브 포트 `VisitLedgerPort`(이 스포크 구현, `app/use_cases/visit_ledger_interactor.py`)로 방문을 묻는다. '앞으로의 예약'은 예약됨·미용 중인 방문이다(날짜가 지났어도).
- 같은 아이(보호자만이면 같은 보호자)의 같은 시각에 살아 있는 예약은 하나다(부분 유일 색인 — 409 `VISIT_DUPLICATE`, 세이브포인트라 트랜잭션은 계속 쓴다).
- 겹침·휴무·영업시간 밖은 **막지 않는 경고**다. 판단은 `domain/services/visit_schedule.warnings_for` 한 곳에만 있다.
- "오늘"과 하루의 경계는 매장 시간대(`ShopContext.timezone`)로 센다. 요청 시각은 시간대가 붙어 와야 하고, 응답 시각은 매장 시간대로 나간다.
- 완료가 생기거나 풀리면 그 보호자의 마지막 완료 방문 시작 시각을 `CustomerDirectoryPort.set_last_visit`로 같은 트랜잭션에서 넘긴다(고객 목록 '최근 방문순'). 어긋나면 `scripts/rebuild_last_visit.py`로 복구한다.
- **미용 기록**(④)은 방문 하나에 하나다(`visit_records` — 몸무게·케어 메모(공개, ⑤ 알림장)·내부 메모·결제 수단·총액(받은 돈, 항목 합과 별개)·실제 메뉴와 금액·사진영상). 미용 중·완료 방문에만 쓴다(409 `VISIT_NO_RECORD_YET`, 판정은 `domain/services/visit_record_rules.py`). 쓰기 셋 — 전체 교체(`PUT …/record`), 사진 하나 덧붙이기(`POST …/record/media`, 그 칸 맨 뒤·빈 기록 생성·같은 미디어 멱등), 삭제(`DELETE …/record`, record:delete) — 모두 방문 쓰기와 같은 잠금(고객 행 → 방문 행)을 거친다. 돈 칸(총액·항목·결제 수단)은 sales:write 다.
- **기록 버전.** 기록을 바꿀 때마다 `version`이 오른다. 전체 교체는 읽은 버전을 보내야 하고(없으면 보내지 않는다) 다르면 409 `RECORD_VERSION_CONFLICT` — 앱의 업로드 대기열이 덧붙인 사진을 폼 저장이 모르고 지우지 않게 한다. 덧붙이기는 버전을 받지 않고 올린다.
- 기록의 사진·영상은 media 의 허브 포트 `MediaLibraryPort`로 가져가고(claim) 놓는다(release) — 둘 다 조건부 UPDATE 라 잠금 안에서 부른다. 놓인 미디어는 media 의 정리 스크립트가 하루 뒤 지운다. `visit_record_media.kind`는 가져가기가 알려 준 값(바뀌지 않는 사실)이다 — 대표 사진(후 → 전 → 영상 포스터, `cover_media_id`)과 한도(사진 30·영상 3)를 이 표만으로 계산한다. 읽기 URL 은 `read_urls`로 받는다(`app/services/record_reader.py`·`cover_reader.py`).
- 기록에 몸무게를 처음 적거나 바꾸면 그 방문이 그 아이의 가장 최근 시작한 방문일 때만 `CustomerDirectoryPort.set_pet_weight`로 현재 몸무게를 넘긴다(`completion_effects.sync_pet_weight`). 같은 몸무게로 메모만 고쳐 저장하거나 옛 기록을 고쳐도 현재 값은 그대로다. 전이는 몸무게를 넘기지 않는다.
- 방문 상세는 기록 전체와 대표 사진, 하루 목록은 `has_record`·`cover`, 달력은 날마다 완료 방문의 `cover`·`covers`(최대 4), 피드(`GET /visits/feed`)는 완료 방문을 완료 시각 역순 커서로 준다. 기록 여러 개는 `VisitRecordRepository.list_many`로 방문 수와 상관없이 한 번에 읽는다.
- **도메인 이벤트를 발행한다**(⑥). 허브 포트 `DomainEventPort`(`dependencies/hub_ports.get_domain_events` 자리, `main.py` 가 core 의 같은 세션 동기 버스를 꽂는다)로 방문의 사실을 알리고 notification 을 모른다. 구독자는 같은 트랜잭션에서 돌고 던지면 요청이 실패한다. 발행 규칙은 아래 표이고, 공통 칸(`ctx`·`visit_id`·`customer_id`·`pet_id`·`starts_at`)은 쓰기 뒤 행의 값, `occurred_at` 은 인터랙터가 한 번 읽은 `now` 다. 되돌리기는 `VisitReserved(revived=True)`(접수 안내 없이 리마인드만), `start` 는 발행하지 않는다. `pet_id` 만 바뀐 수정도 발행하지 않는다. `family_pet_ids` 는 그 명령이 함께 다룬 같은 보호자·같은 `starts_at` 방문들의 `pet_id`(None 제외, 오름차순) — 등록·일정 변경은 명령의 방문 전부, 전이는 같은 `starts_at` 끼리, 수정·알림장은 방문 하나라 자기 아이뿐이다.

| 인터랙터 | 발행 | 위치 |
|---|---|---|
| `RegisterVisitInteractor` | 만든 방문마다 `VisitReserved(revived=False)` — `status == reserved` 일 때만(`walk_in` 은 없음) | `create_many` 뒤, 경고 계산 앞 |
| `UpdateVisitInteractor` | `starts_at` 이 바뀌었을 때만 `VisitRescheduled(previous_starts_at)` | `update_details` 뒤 |
| `RescheduleVisitsInteractor` | 옮긴 방문마다 `VisitRescheduled(previous_starts_at=잠근 행의 starts_at)` | `reschedule` 뒤, `ensure`·경고 앞 |
| `TransitionVisitsInteractor` | `cancel` → `VisitCanceled(reason)`, `complete` → `VisitClosed("completed", previous_completed_at=latest_completed_start_excluding(…))`, `no_show` → `VisitClosed("no_show", None)`, `revert` → `VisitReserved(revived=True)` | `apply_changes`·`apply_completion_effects` 뒤, 응답 앞 |
| `SendVisitReportInteractor` | 새 링크를 만들었을 때만 `VisitReportIssued(url, expires_at)` — 살아 있는 링크의 다시 공유는 발행하지 않는다 | `describe_link` 뒤, 응답 앞 |
| `RevokeVisitReportInteractor` | 살아 있는 링크를 끊었을 때 `VisitReportRevoked` — 끊을 것이 없으면(404) 발행하지 않는다. 익명화가 끊는 링크는 이벤트 없음 | `revoke` 뒤 |

- customer 에 `VisitLedgerPort.latest_covers`(사진이 붙은 가장 최근 완료 방문의 대표 — 반려동물 프로필 사진)를 준다. 익명화(`clear_customer_memos`)는 방문 메모와 기록의 두 메모를 비우고 사진은 남긴다.
- 매장 일정 설정 행은 매장을 처음 쓸 때(조회에서도) 기본값으로 만들고 같은 트랜잭션에서 기본 메뉴를 넣는다. 메뉴는 지우지 않고 보관한다.
- 카톡 예약 초안(`POST /visit-drafts`)은 **아무것도 저장하지 않는다.** 글은 `app/ports/output/visit_draft_parser_port.py` 뒤의 규칙 어댑터(`adapter/outbound/rule_draft_parser_adapter.py` → `domain/services/draft_parser.py`)가 날짜·시각·메뉴·낱말로 읽고, "누구"는 허브 포트 `CustomerDirectoryPort.find_draft_candidates`가 낱말로 찾는다(최대 5 가족). 글과 낱말을 로그·DB·오류 응답에 남기지 않는다(설계 10절 V9). ⑨ 이후 LLM 해석은 같은 포트 뒤에서 어댑터만 바꾼다.
- **미용 알림장**(⑤)은 새 스포크가 아니라 방문 위에 쌓인다. 링크 하나가 `visit_reports`의 한 줄이고 매장은 방문에서 읽는다(`shop_id` 칸이 없다). '살아 있음'은 끊지 않았고 기간이 남은 것이다(`VisitReport.is_live`, 끝나는 바로 그 시각은 닫힘). '보냄'은 저장하지 않고 살아 있는 줄이 있는지로 계산한다.
- **방문당 끊지 않은 줄은 하나다**(부분 유일 색인 `uq_visit_reports_live`). 색인에 지금 시각을 넣을 수 없으므로 **발급이 먼저 닫는다** — 보내기는 `lock_visits` → `close_expired` → `get_live` → 없을 때만 `create` 순서다. `create`는 유일 위반을 바꾸지 않고 그대로 던지므로 이 순서를 어기지 않는다. 기간이 지나 닫힌 줄도 `revoked_at`이 찍힌다.
- **토큰은 저장하지 않고 계산한다.** DB 에는 `public_id`(16바이트)만 있고 토큰은 `public_id + HMAC`(43글자)을 요청마다 다시 만든다(`domain/services/report_token.py`, 키는 `core/config.py`의 `REPORT_LINK_KEY`). 키를 바꾸면 모든 링크가 닫힌다. 토큰을 로그·문서·커밋에 남기지 않는다.
- `PUT …/report` 하나가 처음 보내기·다시 공유·보낸 뒤 사진 빼기를 맡는다. `hidden_media_ids`는 "뺄 것 전부"다 — 목록에 없는 것은 앞서 뺐더라도 되살아난다. 빈 알림장(`REPORT_EMPTY`)은 링크를 새로 만들 때만 본다. 링크의 기간은 만들 때 정해지고 그 뒤 설정을 바꿔도 그대로다.
- **뺀 사진 표시는 링크가 아니라 사진 줄에 붙는다**(`visit_record_media.hidden_from_report`). 링크를 끊고 새로 보내도 빠져 있다. 기록 저장이 미디어 줄을 지우고 다시 넣으므로 **기록 저장이 표시를 이어 붙인다** — 전체 교체는 `carry_hidden`, 덧붙이기는 `append_media`가 있던 미디어의 순서만 바꾼다. 새로 붙인 미디어는 보인다.
- 알림장의 내용은 `app/services/report_reader.py` 한 곳이 조립한다(미리보기·보내기 응답·공개 조회가 함께 쓴다). 보이는 미디어의 순서(후 → 전)와 대표는 `report_rules.visible_media`·`report_cover_media_id`가 정한다 — 저장소가 주는 순서를 그대로 쓰지 않는다.
- 알림장 설정(`GET·PUT /report-settings`)은 `visit_shop_settings`의 칸 다섯이다. 조회는 행을 만들지 않고 없으면 기본값을 준다. 수정은 `ScheduleRepository.ensure` 뒤에 쓴다 — 알림장 설정을 처음 저장하는 매장에는 일정 설정 행과 기본 메뉴가 함께 생긴다. 보여 줄 항목은 조회할 때마다 읽어 이미 보낸 알림장에도 바로 적용된다.
- **살아 있는 링크가 있는 방문은 되돌리거나 기록을 지울 수 없다**(409 `VISIT_REPORT_SENT`). 되돌리기는 `CompletedState.revert`가 `Visit.has_live_report`를 보고, 기록 삭제는 인터랙터가 본다. 둘 다 **잠근 뒤에** 링크를 읽는다. 전이는 행동과 상관없이 링크를 한 번 읽는다(`live_visit_ids`).
- 방문 상세에는 `report`(링크 상태), 하루 목록·피드의 항목에는 `report_sent`가 있다. 방문 여러 개의 링크는 `live_visit_ids`로 한 번에 읽는다. 달력은 바꾸지 않았다.
- **익명화가 링크를 끊는다.** `clear_customer_memos`가 같은 트랜잭션에서 그 고객 방문의 끊지 않은 링크를 모두 끊는다(기간이 지난 줄도). 익명화한 고객의 방문에는 다시 보낼 수 없다 — 가족 잠금이 404 `CUSTOMER_NOT_FOUND`로 거절한다.
- **공개 조회**(`GET /v1/public/report`, `POST /v1/public/report/viewed`)는 로그인이 없고 토큰을 헤더 `X-Report-Token`으로 받는다. 판정은 `app/services/public_report_gate.py` 한 곳이고 순서는 분당 한도(429) → 서명 확인 → (틀리면) 실패가 찼으면 429, 아니면 세고 404 → (맞으면) 링크 찾기(없으면 세고 404) → 살아 있음(410) → 매장(410) → 기록(410)이다. 닫힌 이유는 가르지 않는다.
- **공개 저장소만 `ShopContext`를 받지 않는다**(`PublicReportRepository.find`·`mark_viewed`). 서명을 확인한 `public_id`로만 부른다. 로그인 없는 요청 경로에서 `ShopContext`를 가드 없이 만드는 곳은 `app/services/public_context.py` 하나다 — 권한이 비어 있고 읽기에만 쓴다.
- **공개 스키마는 매장용과 따로다**(`schemas/public_report_schema.py`). 칸을 하나하나 적고 ID·내부 메모·결제 수단·보호자 정보의 칸이 없다. 매장이 끈 항목은 null 이 아니라 칸이 없고, 켰지만 값이 없으면 null 이다. 새 칸을 더하는 것은 공개 범위를 넓히는 일이다.
- 횟수 제한은 분당 60회를 모두에게 건다(조회와 열람 신호가 같은 통). **실패 수 차단은 서명이 틀린 요청에만 건다** — 틀린 토큰은 10분에 20번까지 404, 그다음부터 429(세지 않는다), 서명이 맞는 토큰은 실패가 몇 번 쌓였든 막히지 않는다(`adapter/outbound/redis/public_report_redis_limiter.py`). 웹 서버가 알려 준 주소(`X-Report-Client-IP`)는 `X-Report-Web-Secret`이 맞을 때만 믿는다. **Redis 에 닿지 못하면 통과시키고** 경고를 남긴다 — 토큰 크기가 1차 방어다.
