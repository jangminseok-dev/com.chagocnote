# ⑫-1 백엔드 — 보호자 기록 모아 보기 · 가족 · 리뷰 주소 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 로그인한 보호자가 아이의 사진·영상을 날짜를 넘어 모아 보고 몸무게 변화를 보며, 가족을 초대해 함께 본다. 매장은 알림장 끝에 리뷰 주소 한 줄을 넣고(알림장마다 뺄 수 있다) 가족 수를 정한다.

**Architecture:** 읽기 둘(사진 모아 보기·몸무게)은 `visit` 의 보호자용 읽기 옆(`guardian_scope` → 저장소 질의). 가족은 `guardian` 스포크(`guardian_links.parent_link_id`, 새 표 `guardian_family_invites`·`guardian_shop_settings`). 리뷰 주소·문구는 `visit_shop_settings`, 알림장마다의 빼기는 `visit_reports.show_review`. 마이그레이션 하나(0024).

**Tech Stack:** FastAPI · SQLAlchemy 2.0 asyncio · Alembic · Redis.

**Spec:** `docs/superpowers/specs/2026-11-16-guardian-archive-design.md`(3.3~3.8, 5.1·5.2, 6절, **8절의 답이 앞선다**), 공통 `2026-11-16-next-designs-common.md`. 앞선 결정 `_docs/decisions/010-guardian.md`. 이 묶음의 결정 기록은 `_docs/decisions/015-guardian-archive.md`(새로 만든다).

## Global Constraints

- **모아 보기에 나오는 미디어 = 보호자가 볼 수 있는 알림장 한 장들에 나오는 미디어의 합**이다: 그 매장·그 고객 · 끊지 않은 알림장(기간은 보지 않는다 — `_sent_to`) · 기록이 있다 · `hidden_from_report` 가 거짓. 같음 테스트로 묶는다.
- 몸무게는 같은 조건의 방문 가운데 기록에 몸무게가 있는 것, **매장의 `report_show_weight` 가 지금 켜졌을 때만**, 최근 24개를 오래된 것부터.
- 정지·폐업한 매장은 읽기 둘이 닫힌다(`guardian_scope`).
- **가족 수는 매장이 정한다**(`guardian_shop_settings.family_max`, 기본 3, 0~10 — 0 이면 초대가 없다, 줄여도 이미 이은 가족은 끊지 않는다). 초대는 **24시간·한 번만**(고정). 새로 만들면 앞의 안 쓴 초대는 죽는다. 가족은 다시 초대하지 못한다. 기본 연결은 여전히 카드당 하나.
- 초대 코드는 43자 무작위(원문 저장 안 함, SHA-256), 백엔드로는 헤더 `X-Family-Invite` 로만, 로그·오류 본문·문서·커밋에 남기지 않는다. 없음·씀·죽음·기간 지남·기본 연결 끝남은 모두 404 `GUARDIAN_INVITE_NOT_FOUND`(가르지 않는다). 가득 차면 409 `GUARDIAN_FAMILY_FULL`. 계정당 시간당 10회.
- **잠금: 유저 행 → 보호자 기본 연결 행 → 가족 초대 행 → 가족 연결 행.** 가족이 스스로 끊을 때도 기본 연결 행부터. 탈퇴는 그 계정이 닿는 기본 연결 행을 ID 오름차순으로.
- 기본 연결이 끝나면(보호자·매장·탈퇴·익명화) 가족 연결도 같은 `ended_by` 로 함께 끝나고 안 쓴 초대가 죽는다.
- 매장에는 가족의 수만 — 이름·계정·이은 날을 싣지 않는다. 보호자에게는 `가족 N` 의 이은 날만.
- 리뷰 주소: `https://` · 300자 · 호스트 있음 · `user@`·공백·제어 문자 없음. 문구: 60자 · 줄바꿈·제어 문자 없음 · `http`·`www.` 를 담지 않는다 · 비우면 기본 문구 `미용이 마음에 드셨다면 후기를 남겨 주세요`. 주소가 없거나 그 알림장이 뺐으면 공개·보호자 한 장에 **두 칸 다 없다**.
- 로그인 없이 열리는 경로는 늘지 않는다.

## Review Focus

1. **모아 보기와 한 장이 어긋난다** — 끊은 알림장·뺀 미디어·다시 보낸 알림장(`close_expired` 뒤)·보호자만의 방문이 섞여도 두 쪽의 미디어가 같다.
2. **가족 잇기와 끊기가 겹친다** — 동시에 둘이 이어 수를 넘거나, 기본 보호자가 모두 끊는 사이 가족이 이어 끊긴 기본 아래 가족이 남는다.
3. **기본 연결이 끝났는데 가족이 계속 본다** — 네 길(보호자·매장·탈퇴·익명화) 각각.
4. **매장이 가족 수를 줄이거나 0 으로 했다** — 이미 이은 가족은 그대로, 새 초대·잇기는 409.
5. **리뷰 주소에 `javascript:`·`http://`·`https://user@host`·공백·300자 초과, 문구에 주소를 심음** — 422, 저장되지 않는다.

---

### Task 1: 리뷰 주소·문구와 알림장마다 빼기

**Files:** `alembic/versions/0024_guardian_archive.py`(이 작업의 칸만 먼저 — Task 2 가 같은 파일에 더한다), `visit` 의 ORM·`ReportSettings`·설정 저장소·설정 스키마(GET 에 `review_text_default`, PUT 의 두 칸은 **빠지면 지금 값** — 앱이 따라올 때까지 다섯 칸만 보내도 지워지지 않게), `report_rules.py`(`check_review_url`·`check_review_text`·`DEFAULT_REVIEW_TEXT`·`review_of(settings, show_review)`), `VisitReport.show_review`·보내기 요청의 선택 `show_review`(기본 참)·저장, `report_reader.describe_report(..., show_review=)` → `ReportView.review_url/review_text`, `PublicReportSchema` 두 칸(없으면 칸째 없음), 미리보기 응답에 `review_url`·`review_text`·`link.show_review`.

- [ ] 단위(RED): 주소 갈래(정상·`http://`·`javascript:`·`https://user@x`·공백·301자·호스트 없음), 문구 갈래(61자·줄바꿈·`www.`·`http`·빈 글 → 기본).
- [ ] 통합(RED): 설정 PUT·GET(빠지면 둔다, 422) / 주소가 없으면 공개 한 장에 두 칸 없음 / 있으면 두 칸(문구 없으면 기본) / `show_review: false` 로 보내면 공개·보호자 한 장에 없음, 다시 보내며 켜면 생김 / 미리보기의 값.
- [ ] 구현 → GREEN → 커밋 `feat(report): 알림장 끝의 리뷰 주소 — 설정·알림장마다 빼기·공개 한 장`.

### Task 2: 가족 — 표·초대·잇기·끊기·매장 설정

**Files:** 0024 에 `guardian_links.parent_link_id`·`seen_by_primary_at`·CHECK(`verified_by` 에 `family_invite`, `ended_by` 에 `primary`)·`uq_guardian_links_live` 조건(`AND parent_link_id IS NULL`)·`uq_guardian_links_family(parent_link_id, user_id)`, `guardian_family_invites`, `guardian_shop_settings(shop_id, family_max)`. `guardian` 의 엔티티·ORM·저장소(잠금 메서드)·유스케이스(초대 만들기·잇기·가족 목록·한 명 끊기·모두 끊기)·기존 끊기 셋과 탈퇴·익명화의 함께 끝내기·연결 목록의 `role`·`family_count`·`family_max`·매장 연결 응답의 `family_count`·매장 설정 `GET·PUT /v1/shops/{id}/guardian-settings`, 제한기 이름 공간(`guardian:invite`), 오류 둘. Test: `tests/integration/test_guardian_family_wiring.py`, 잠금 `test_guardian_family_locking.py`, 단위(초대 규칙).

**Interfaces — Produces:** `POST /v1/me/guardian/links/{link_id}/family-invites` → 201 `{code, expires_at}` / `POST /v1/me/guardian/family-links`(헤더 `X-Family-Invite`) → 201·200 `{link_id}` / `GET /v1/me/guardian/links/{link_id}/family` → `{items: [{family_id, linked_at, unseen}]}` / `DELETE …/family/{family_id}`·`DELETE …/family` → 204 / 연결 목록 항목에 `role`·`family_count`·`family_max` / 매장 `GET …/guardian-link` 에 `family_count` / `GET·PUT /v1/shops/{id}/guardian-settings {family_max}`(+ `defaults`).

- [ ] 단위·통합(RED): 만들기(기본만 — 가족은 404, 다시 만들면 앞의 것 죽음, 수가 차면 409, 0 이면 409) / 잇기(201·자기 것 200·이미 가족 200·쓴·죽은·기간 지난·모르는 코드 404·가득 409·제한 429) / 가족이 같은 기록을 읽는다(알림장 목록) / 목록의 이은 날·`unseen` 한 번 / 한 명 끊기·모두 끊기(남의 `family_id` 404) / 네 길의 함께 끝내기 / 매장 설정(기본 3, 범위 422, 줄여도 가족 그대로) / 매장 응답에 수만 / 동시 잇기 둘이 수를 넘지 않는다·모두 끊기와 잇기가 겹쳐도 끊긴 기본 아래 가족이 없다(잠금 테스트).
- [ ] 구현 → GREEN → 스키마 대조·계약 → 커밋 `feat(guardian): 가족과 함께 보기 — 초대·잇기·끊기, 매장이 정하는 가족 수`.

### Task 3: 사진 모아 보기와 몸무게

**Files:** `visit` 의 `GuardianReportRepository` 에 `list_media(ctx, customer_id, *, pet_id, year, phase, before, limit)`·`media_years(ctx, customer_id, *, pet_id)`·`weights(ctx, customer_id, pet_id, limit)`, 커서(방문 시각·방문 ID·전후·순서), 유스케이스 둘, 경로 `GET /v1/me/guardian/links/{link_id}/media`·`…/pets/{pet_id}/weights`(헤더 `PUBLIC_REPORT_HEADERS`). Test: `tests/integration/test_guardian_archive_wiring.py`.

- [ ] 통합(RED): **같음 테스트**(끊기·뺀 미디어·보호자만의 방문·다시 보내기 섞음 — 한 장들의 미디어 = 모아 보기를 끝까지 넘긴 미디어) / 60개 쪽·다음 쪽·깨진 커서 422 / 거르기(아이·연도·전후) / `years` / 몸무게(꺼짐이면 비어 있음, 켬이면 오래된 것부터, 기록에 몸무게 없는 방문 빠짐, 받은 적 없는 아이 404) / 정지한 매장 404 / 남의 연결 404 / 가족 연결도 같은 것을 본다.
- [ ] 구현 → GREEN → 커밋 `feat(guardian): 아이의 사진 모아 보기와 몸무게 변화`.

### Task 4: 흐름·문서

- [ ] `backend/scripts/check_guardian_flow.sh` 에 리뷰 줄·가족(초대 → 다른 계정이 잇기 → 같은 기록 → 기본이 그 한 명만 끊기 → 매장의 끊기가 가족까지)·모아 보기·몸무게 단계. 흐름을 돌린 뒤에 기록한다.
- [ ] 문서: 루트 `CLAUDE.md`(잠금 문단 한 줄), `apps/guardian/CLAUDE.md`, `apps/visit/CLAUDE.md`, `_docs/decisions/015-guardian-archive.md`(정한 것·Ruling·API 계약), `_docs/harness.md`.
- [ ] 단위·통합·계약·흐름(`check_guardian_flow.sh`·`check_report_flow.sh` 가 있으면) → 커밋.

### 끝

최종 검토(새 맥락, model fable, 이 Review Focus) → Critical·Important 는 테스트 먼저 한 번의 수정 → 015 → 메모리 → 보고(병합 메뉴). 그 뒤 ⑫-2 웹·⑫-3 앱.
