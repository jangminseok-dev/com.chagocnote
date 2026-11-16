# ⑬-1 백엔드 — 미용 주기 · 다시 올 때가 된 아이 · 결제 완료와 남은 일 · 하루 마무리 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 아이마다 미용 주기를 한 곳에서 계산해 다음 예약 초안·알림 줄·다시 올 때가 된 아이 목록이 같은 값을 쓰고, 하루·달력·피드가 결제 완료와 남은 일(결제 안 적음·알림장 안 보냄)을 싣고, 하루 마무리가 그날의 남은 일을 장으로 낸다.

**Architecture:** 계산은 visit 의 순수 함수(`domain/services/visit_cycle.py`). 아이의 직접 정한 주기·안내한 날은 customer 의 `pets` 두 칸이고 visit 은 허브 포트 `CustomerDirectoryPort.revisit_facts` 로 읽는다. 반려동물 상세는 `VisitLedgerPort.pet_revisit` 로 주기를 받는다. 매장의 값 여섯은 `visit_shop_settings` 이고 새 경로 `revisit-settings` 로 읽고 쓴다. 알림 쪽은 `VisitClosed` 의 새 칸으로만 받는다. 마이그레이션 0025.

**Tech Stack:** Python 3.13 · FastAPI · SQLAlchemy 2.0 asyncio · Alembic · pytest.

**Spec:** `docs/superpowers/specs/2026-11-16-grooming-cycle-design.md`(10절의 답이 앞선다 — 계산의 속 둘을 매장이 바꾼다), 공통 `2026-11-16-next-designs-common.md`. 결정 기록 `_docs/decisions/016-grooming-cycle.md`(새로).

## Global Constraints

- 주기(3.1): 직접 정한 값(1~52) → 계산한 값(최근 `cycle_sample_visits`(기본 6, 3~12)번의 완료 방문, 매장 시간대 날짜, 이웃 간격 가운데 `cycle_min_gap_days`(기본 7, 0~28) 미만은 버림, 730일보다 오래된 방문은 보지 않음, **간격 둘 이상일 때만**, 중앙값(짝수 개면 가운데 둘의 평균)을 주로 반올림해 1~52) → 간격 하나 `single`·없음 `none` 은 날짜에 매장의 기본 간격(`default_cycle_weeks`, 기본 4)을 쓰고 `estimated`. 계산은 읽을 때 하고 저장하지 않는다.
- 다음 올 때 = 마지막 완료 방문의 날 + 날짜에 쓰는 주. 묶음: **곧** = 출처 manual·computed 이고 다음 올 때가 오늘~오늘+`revisit_soon_days`(기본 7, 1~30)일, **지남** = 다음 올 때 < 오늘(어림 포함). 공통 조건 ⑧ 그대로(마지막 완료 1년 안, 앞날 예약(오늘 0시 이후 reserved·in_progress) 없음, `showable_pets`, 무지개다리 아님). 매출 요약 `due_pet_count` = 지남의 수.
- `paid` = 기록의 총액이 있고 (나머지 0 이거나 결제 수단이 있다), 나머지 = 총액(⑭·⑮ 전). `marks` = `paid`·`report_sent` 의 이 순서(⑭·⑮ 가 뒤에 더한다). **남은 일**: `unpaid` = 완료이고 `paid` 아님, `report_unsent` = 완료이고 기록이 있고 알림장 줄이 **한 번도** 없고 `report_skipped_at` 이 비었고 매장의 `count_unsent_reports` 가 켜짐, `unresolved` = 지금 규칙(지난 날의 reserved). 지난 날·오늘만.
- 새 응답 칸(목록·수·`marks`·하루 마무리)에 **금액 숫자가 없다** — 하루 마무리의 결제 장의 채움 값(총액·수단)은 `sales:write` 가 있을 때만 장이 나온다.
- 안내 글 기본: `안녕하세요, {매장}예요.\n{아이}가 미용한 지 {주}주가 됐어요.\n편하신 날 알려 주시면 예약 잡아 드릴게요.` — 템플릿·만든 글을 로그·오류에 싣지 않는다. 템플릿 300자, 빈 글 거절.
- 잠금: 주기·안내한 날 쓰기는 customer 의 가족 잠금(고객 행)부터, `report-skip` 은 `lock_family` → 방문 행. 새 잠금 줄 없음. `SearchSourceChanged` 를 내지 않는다.
- 권한: 새 권한 없음. 목록·수·달력·하루·하루 마무리 읽기 = 매장 멤버, 주기·안내한 날 쓰기 = `customer:write`, `revisit-settings` 쓰기 = `shop:update`, `report-skip` = `record:write`.

## Review Focus

1. 2주 간격으로 두 번 온 아이(간격 하나)가 15일째에 '지남'에 오르거나 '곧'에 들어간다 — `single` 은 날짜에 기본 간격을 써야 한다.
2. 매장 시간대 자정 앞뒤의 완료 방문·'곧'의 경계(오늘+7일 당일·다음 날)에서 하루 어긋난다.
3. 기간이 지난(7일) 알림장 링크의 방문이 다시 "알림장 안 보냄"에 뜬다 — 남은 일은 "줄이 있었는가"로 본다.
4. 목록이 아이 수만큼 질의하거나 달력이 주기 계산·`revisit_facts` 를 부른다(호출 수 고정 테스트).
5. 가족 묶음의 알림 줄에 둘째 아이가 합쳐질 때 더 짧은 주로 당겨지지 않거나, 아이의 직접 정한 값보다 매장 고정 주 수가 앞선다.

## Rulings (계획 때 정함 — 설계와 다른 곳)

- **아이의 주기·안내한 날은 `care_facts` 가 아니라 새 포트 메서드 `revisit_facts(ctx, pet_ids) -> dict[int, PetRevisitFact]` 로 읽는다** — `care_facts` 는 서명·서류·서류 설정까지 읽어 수백 마리의 목록과 완료마다 부르기에 무겁다. 틀리면: 포트 메서드가 하나 더 있다.
- **매장의 값 여섯은 새 경로 `GET·PUT /revisit-settings`**(값은 `visit_shop_settings`) — 지금의 `visit-settings` PUT 은 네 칸 필수 전체 교체라 쓰는 자리의 한 칸 바꾸기에 맞지 않는다. PUT 은 빠진 칸을 지금 값으로 둔다(⑫ 의 `kept()` 선례). `shop:update`(사장만) — 쓰는 자리의 바꾸기 링크도 사장에게만.
- **하루 마무리의 장은 방문 하나에 한 장**(설계는 "가족 묶음은 한 장") — 기록·알림장이 방문마다라 묶음 한 장에는 여러 총액을 적는 폼이 필요하다. 틀리면: 둘 온 가족은 장이 둘이다.
- **"알림장 안 보냄"은 알림장 줄이 한 번도 없는 것**(링크가 끝나거나 끊겨도 보낸 것). 줄의 `report_sent` 낱말은 지금 뜻(살아 있는 링크) 그대로.
- 반려동물 상세의 `has_upcoming` 은 목록과 같은 뜻(오늘 0시 이후 reserved·in_progress).
- 안내한 날의 "오늘"은 customer 의 `seoul_today`(동의 받은 날과 같다).
- `VisitClosed` 에 칸 셋(`cycle_weeks: int | None = None`(직접·계산일 때만), `cycle_source: str = "none"`, `default_cycle_weeks: int = 4`)을 `family_pet_ids` 앞에 — 알림 쪽이 매장의 기본 간격을 모르므로 함께 싣는다.
- 쓰기 `PUT|DELETE …/pets/{id}/grooming-cycle`·`PUT …/pets/{id}/revisit-nudge` 는 204 — 앱이 상세를 다시 읽는다.
- `GET …/sales/due-pets` 와 그 유스케이스·스키마를 지운다(아직 배포 전 — ⑬-2 가 앱을 옮긴다).

---

### Task 1: 칸과 주기 함수, 매장의 값

마이그레이션 `0025_grooming_cycle.py`: `pets.grooming_cycle_weeks smallint null CHECK 1~52`, `pets.revisit_nudged_on date null`, `visit_shop_settings` 칸 여섯(설계 4.1 + 10절), `visits.report_skipped_at timestamptz null`. ORM 둘. `visit_cycle.py` 를 `pet_cycle(completed_days: list[date], *, manual_weeks: int | None, rules: CycleRules, today: date) -> PetCycle` 로 바꾼다(`PetCycle{weeks, source, interval_count, last_interval_weeks, last_visit_date, due_date, estimated}`, `CycleRules{default_weeks, sample_visits, min_gap_days, soon_days}`)와 `bucket_of(cycle, today, soon_days) -> 'soon'|'due'|None`, `next_start` 는 그대로. 값 객체 `RevisitSettings`(여섯 칸, 범위 검사), 저장소 읽기·부분 쓰기, `GET·PUT /v1/shops/{id}/revisit-settings`(`defaults` 함께). 테스트(RED 먼저): 중앙값·짝수·버리기·0일·2년·1~52 자르기·manual 우선·single/none 의 estimated·간격 둘의 computed, 곧·지남 경계(당일·+7·+8·어제), 설정 범위 422·빠진 칸 유지·사장만.

### Task 2: customer — 아이의 두 칸과 쓰기, 허브 포트

`PUT|DELETE /v1/shops/{id}/pets/{pet_id}/grooming-cycle`(`{weeks}` 1~52), `PUT …/revisit-nudge`(본문 없음, `seoul_today`), `customer:write`, 고객 행 잠금, 204. 익명화가 두 칸을 비운다. 허브 `CustomerDirectoryPort.revisit_facts`(`PetRevisitFact{grooming_cycle_weeks, revisit_nudged_on}`, 질의 하나), `VisitLedgerPort.pet_revisit(ctx, pet_id, manual_weeks) -> PetRevisitView`(visit 이 구현 — 완료 날짜 읽기·매장 값·앞날 예약). 반려동물 상세 응답에 `revisit`(`cycle_weeks, cycle_source, interval_count, last_interval_weeks, last_visit_date, due_date, estimated, has_upcoming, nudged_on`). 가짜 셋 갱신. 테스트: 쓰기·범위 422·남의 매장 404·직원 가능·익명화, 상세의 네 출처, 포트 가짜.

### Task 3: 다음 예약 초안과 알림 줄

`get_next_visit_draft_interactor` 가 `pet_cycle` 을 쓴다(`revisit_facts` 한 번, 완료 날짜 `sample_visits` 만큼) — 응답에 `cycle_weeks`·`cycle_source`(남기는 `interval_weeks` = `cycle_weeks`). 보호자만의 방문은 `none`. `transition_visits_interactor` 의 complete 가 `VisitClosed` 의 새 칸 셋을 채운다(설정·`revisit_facts`·완료 날짜). notification `_closed` 의 주 수 순서: 아이의 manual → 매장 알림 고정 주 수 → computed → `default_cycle_weeks`. 묶음 줄에 합칠 때 더 짧으면 보낼 때와 `interval_weeks` 를 당긴다. 테스트: 초안의 세 출처와 날짜가 늘 있다(완료 한 번), 주 수 순서 넷, 묶음의 짧은 쪽, 이벤트 기본값(예전 발행).

### Task 4: 다시 올 때가 된 아이 — 목록과 수

후보 질의(마지막 완료 1년 안·앞날 예약 없음, 아이별 최근 완료 날짜 `sample_visits` 개 — 창 함수 한 번) → `showable_pets`·무지개다리 → `revisit_facts` 한 번 → `pet_cycle`·`bucket_of`. `GET /v1/shops/{id}/revisits?bucket=soon|due&cursor=`(20개, 지남은 오래 지난 순·곧은 가까운 순, 항목: 아이 카드·`last_visit_date`·`last_visit_id`·`cycle_weeks`·`cycle_source`·`last_interval_weeks`·`due_date`·`estimated`·`nudged_on`(마지막 완료보다 뒤일 때만)·`message`), `GET …/revisits/counts`(`{soon, due}`), 멤버. 매출 요약의 `due_pet_count` 가 같은 함수의 지남. `/sales/due-pets` 를 지운다. 테스트: 격리, 두 묶음·공통 조건(앞날 예약·무지개다리·익명화·1년), single 15일째, 수와 목록이 같다, 직원 200, 호출 수 고정, 안내 글 채움(매장·아이·주).

### Task 5: 결제 완료와 남은 일 — 하루·달력·피드, 알림장 넘기기

순수 함수 `is_paid(record)`·`marks_of(...)`. 하루 응답 항목에 `marks`, `counts` 에 `unpaid`·`report_unsent`·`checks`(`DayCountsView.of` 의 제외 목록). 달력의 날마다 `unpaid_count`·`report_unsent_count`(지난 날·오늘, 알림장 줄은 그달 완료 방문에 대해 한 번 읽는다), 달력은 `revisit_facts`·주기를 부르지 않는다. 피드 항목에 `marks`. `PUT|DELETE /v1/shops/{id}/visits/{id}/report-skip`(`record:write`, 완료이고 기록이 있는 방문만, 잠금). 방문 상세에 `report_skipped`. 테스트: paid 표(총액 없음·수단 없음·0원·둘 다), 기간 지난 링크는 안 보냄이 아니다, 넘긴 방문은 세지 않는다, 매장 설정 끄면 세지 않는다, 앞날 0, 금액 칸 없음.

### Task 6: 하루 마무리 읽기

`GET /v1/shops/{id}/days/{date}/wrap-up` → `{cards: [{kind: unresolved|unpaid|report_unsent, visit_id, starts_at, pet{...}, customer_name?, menus, prefill?}]}` — 차례 unresolved → unpaid → report_unsent, 그 안에서 시작 시각·방문 ID 순. 권한 없는 종류는 빠진다(`reservation:write`·`sales:write`·`record:write`). 결제 장의 `prefill{total_amount, payment_method}` = 기록의 총액(없으면 메뉴 값의 합), 그 고객의 가장 최근 결제 수단(질의 하나). 앞날은 빈 목록. 테스트: 세 종류·차례·권한·채움·넘긴 알림장·격리.

### Task 7: 흐름 스크립트 · 문서

`backend/scripts/check_revisit_flow.sh`(설계 7절의 차례), `apps/visit/CLAUDE.md`·`apps/customer/CLAUDE.md`·`apps/notification/CLAUDE.md`, `_docs/harness.md`, 라우트 표, `_docs/decisions/016-grooming-cycle.md`(사용자 결정·Ruling·API 계약). 단위·통합·계약·흐름.
