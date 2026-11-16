# 016 — ⑬ 미용 주기 · 다시 올 때가 된 아이 · 결제 완료와 남은 일 · 하루 마무리

2026-11-17. 설계 `docs/superpowers/specs/2026-11-16-grooming-cycle-design.md`(10절의 답이 앞선다), 공통 `2026-11-16-next-designs-common.md`, 계획 `docs/superpowers/plans/2026-11-17-cycle-13-backend.md`. 마이그레이션 0025. 011(매출)의 `GET /sales/due-pets` 와 "57일~365일" 규칙은 이 기록이 대신한다.

## 사용자가 정한 것 (2026-11-17)

- **주기 계산의 속도 매장이 바꾼다** — 최근 몇 번(`cycle_sample_visits` 기본 6, 3~12)과 며칠 안에 다시 온 방문을 뺄지(`cycle_min_gap_days` 기본 7, 0~28)를 예약 설정에서 고친다.
- 묻지 않고 공통 12절의 기본값을 따른 것: 모를 때의 기본 간격 4주(`default_cycle_weeks`, 1~52), 알림장을 남은 일로 세기 기본 켬(`count_unsent_reports`). 둘 다 매장이 바꾼다.

## ⑬-1 백엔드에서 정한 것 (계획 때 — 설계와 다른 곳)

- 아이의 주기·안내한 날은 `care_facts` 가 아니라 새 허브 포트 메서드 `CustomerDirectoryPort.revisit_facts(ctx, pet_ids)` 로 읽는다 — `care_facts` 는 서명·서류까지 읽어 수백 마리의 목록과 완료마다 부르기에 무겁다.
- 매장의 값 여섯은 새 경로 `GET·PUT /revisit-settings` — 지금의 `visit-settings` PUT 은 네 칸 필수 전체 교체라 쓰는 자리의 한 칸 바꾸기에 맞지 않는다. PUT 은 빠진 칸을 지금 값으로 둔다(⑫ 의 선례). 쓰기는 `shop:update`(사장).
- **하루 마무리의 장은 방문 하나에 한 장**(설계는 "가족 묶음은 한 장") — 기록·알림장이 방문마다라 묶음 한 장에는 여러 총액을 적는 폼이 필요하다. 둘 온 가족은 장이 둘이다.
- **"알림장 안 보냄"은 알림장 줄이 한 번도 없는 것** — 링크가 끝나거나 끊겨도 보낸 것이다. 줄의 `report_sent` 낱말은 지금 뜻(살아 있는 링크) 그대로.
- 반려동물 상세의 `has_upcoming` 은 목록과 같은 뜻(오늘 0시 이후 예약됨·미용 중). 안내한 날의 "오늘"은 customer 의 `seoul_today`(동의 받은 날과 같다).
- `VisitClosed` 에 칸 셋(`cycle_weeks: int | None = None`(직접·계산일 때만), `cycle_source: str = "none"`, `default_cycle_weeks: int = 4`) — 알림 쪽이 매장의 기본 간격을 모르므로 함께 싣는다. 예전 발행(칸 없음)은 기본값으로 읽힌다.
- 주기·안내한 날 쓰기는 204 — 앱이 상세를 다시 읽는다.
- `GET /sales/due-pets` 와 그 유스케이스·스키마를 지웠다(배포 전 — ⑬-2 가 앱을 옮긴다).

### 실행하면서 정한 것 (Ruling)

- 다음 예약 초안의 가족은 아이들의 주기 가운데 **짧은 쪽**(기본 간격 포함) — 알림 줄의 묶음 규칙(짧은 쪽으로 당김)과 같다. 틀리면: 둘 온 가족의 초안 날짜가 하나 앞이다.
- 알림장 넘기기 유스케이스는 `VisitWriteRepository` 를 받는다(방문 행을 쓴다) — 쓰기 포트를 받는 유스케이스가 다섯이 됐다.
- `paid` 는 완료 방문에만 붙는다 — 미용 중에 총액을 적어도 아직 아니다. 남은 일 '결제 안 적음'과 같은 바탕.
- 하루 마무리 경로는 설계 그대로 `GET /days/{date}/wrap-up`.
- **익명화한 고객의 방문은 남은 일이 아니다** — 하루 머리·달력·하루 마무리 모두. 기록·알림장·넘기기가 가족 잠금 404 라 끝낼 수 없는 장이 영영 남기 때문이다. 달력은 그달 완료 방문의 고객 요약을 한 번 더 묻는다.
- **하루 머리·달력의 남은 일도 지난 날·오늘만** — 앞날에 일찍 끝낸 방문은 세지 않는다(하루 마무리가 앞날에 비는 것과 맞춘다).
- 결제 장의 채움: 총액은 기록 총액 → 기록 항목 합 → 예약 메뉴의 정가 합(값 없는 메뉴는 빼고, 없으면 null — 앱의 기록 화면 채움 규칙), 수단은 기록의 것 → 그 고객이 수단을 적은 기록 가운데 방문 시작이 가장 늦은 것(같은 날 뒤의 방문이어도). 둘 다 앱에서 고칠 수 있다.
- 장의 사진은 아이의 프로필 사진(사진이 붙은 가장 최근 완료 방문의 대표), 장의 방문은 하루 목록과 같은 모양.
- 안내 글의 `{주}` 는 주기가 아니라 **마지막 미용 뒤 지난 주**다("미용한 지 N주가 됐어요").

## API (⑬-1 이 더하거나 바꾼 것)

모두 `/v1/shops/{shop_id}` 아래. 새 응답 칸 어디에도 금액 숫자가 없다(결제 장의 `prefill` 은 `sales:write` 가 있을 때만 나오는 장의 채움 값).

**`GET /revisit-settings`**(멤버) → `{default_cycle_weeks, revisit_soon_days, revisit_message|null, count_unsent_reports, cycle_sample_visits, cycle_min_gap_days, defaults{같은 여섯 칸 — revisit_message 는 처음 글}}`. **`PUT /revisit-settings`**(`shop:update`) — 같은 칸의 일부, 빠진 칸은 지금 값, `revisit_message: null` 은 처음 글로. 범위 밖·빈 글·301자·방향 문자는 422.

**`PUT /pets/{pet_id}/grooming-cycle`** `{weeks: 1~52}` · **`DELETE …`**(계산으로 돌아가기) · **`PUT /pets/{pet_id}/revisit-nudge`**(본문 없음, 오늘) — `customer:write`, 204, 남의 아이 404.

**`GET /pets/{pet_id}`** 에 `revisit{cycle_weeks, cycle_source(manual|computed|single|none), interval_count, last_interval_weeks|null, last_visit_date|null, due_date|null, estimated, has_upcoming, nudged_on|null}`.

**`GET /visits/{visit_id}/next-draft`** 에 `cycle_weeks`·`cycle_source`(`interval_weeks` 는 같은 값으로 남긴다).

**`GET /revisits?bucket=soon|due&cursor=`**(멤버) → `{items: [{pet: PetCard, last_visit_date, last_visit_id, cycle_weeks, cycle_source, last_interval_weeks|null, due_date, estimated, nudged_on|null, message}], next_cursor}` 20개 — 지남은 오래 지난 순, 곧은 가까운 순. **`GET /revisits/counts`** → `{soon, due}`. 매출 요약의 `due_pet_count` 는 `due` 와 같다.

**`GET /visits?date=`**: 항목에 `marks: ["paid"|"report_sent", …]`(이 차례, 앱은 아는 코드만), `counts` 에 `unpaid`·`report_unsent`·`checks`. **`GET /visits/calendar?month=`**: 날마다 `unpaid_count`·`report_unsent_count`. **`GET /visits/feed`**: 항목에 `marks`. **`GET /visits/{visit_id}`**: `marks`·`report_skipped`.

**`PUT|DELETE /visits/{visit_id}/report-skip`**(`record:write`, 204) — 넘기기는 완료이고 기록이 있는 방문만(아니면 409 `VISIT_STATE_CONFLICT`), 되돌리기는 언제나. 남의 방문 404.

**`GET /days/{date}/wrap-up`**(멤버) → `{date, cards: [{kind: unresolved|unpaid|report_unsent, visit: Visit, photo_url|null, prefill{total_amount|null, payment_method: card|cash|transfer|null}|null}]}`. 차례는 종류 → 시작 시각 → 방문 ID. 장을 끝내는 권한(`reservation:write`·`sales:write`·`record:write`)이 없는 종류는 빠진다. 앞날은 빈 목록, 날짜가 틀리거나 2000~2100 밖이면 422.

**지운 것**: `GET /sales/due-pets`.

이벤트: `VisitClosed` 의 `cycle_weeks`·`cycle_source`·`default_cycle_weeks`. notification 의 다음 예약 제안 주 수는 아이의 직접 정한 주기 → 매장 알림 설정의 고정 주 수 → 계산한 주기 → 매장의 기본 간격, 묶음 줄은 짧은 쪽으로 당긴다.

### 흐름 확인

2026-11-17 — `backend/scripts/check_revisit_flow.sh`(새로) 아홉 단계·확인 36줄을 개발 스택(게이트웨이)에서 모두 통과했다: 방문 몇 번 → 주기를 손계산(35·35일 → 5주, 50일 → 7주, 한 번 → 기본 4주 어림)과 견줌 → 곧·지남과 수, 매출 요약의 수 → 직접 정하기·지우기 → 예약을 잡으면 빠짐 → 안내한 날 → 어제의 남은 일과 하루 마무리의 장 → 금액을 적으면 `paid` 이고 장이 줄어듦 → 보내지 않음·되돌리기 → 기본 간격을 바꾸면 묶음이 바뀜 → 직원 403·로그인 없이 401. 안내 글은 찍지 않는다(아이 이름이 들었는지만 본다).
