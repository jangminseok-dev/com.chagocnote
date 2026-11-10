# ⑥-1b 알림톡 백엔드 보완 (I6 가족 묶음 · I7 문안 판 올림) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 아직 안 나간 가족 묶음 알림톡이 "지금 그 시각에 오는 아이들"을 싣게 하고, 승인된 템플릿을 새 판으로 재등록해도 심사 동안 옛 판으로 끊김 없이 나가게 한다.

**Architecture:** I6 은 순수 규칙(도메인 서비스 `family_group.py`) + 저장소 메서드 셋 + 구독자 인터랙터의 빼기·더하기로 푼다. 아이별 방문 ID 는 줄의 `variables.pet_visits` 에 적어 visit 을 조회하지 않고 줄을 옮긴다. I7 은 `notification_templates` 에 대기 칸 둘(0013)을 더하고 `upsert` 가 승인된 줄을 덮지 않게 하며, 디스패처·스크립트가 대기 판의 심사 결과를 올리거나 버린다.

**Tech Stack:** Python 3.13 · SQLAlchemy 2.0 asyncio · Alembic · pytest. 전부 `infra/` 에서 docker compose 로 돌린다.

**Spec:** `docs/superpowers/specs/2026-11-10-notification-6-1b-design.md` (바탕: `docs/superpowers/specs/2026-10-14-notification-design.md`, `_docs/decisions/009-notification.md`)

## Global Constraints

- 주석·문서·테스트 이름·커밋 메시지는 한국어. 테스트는 먼저 쓰고 떨어지는 것을 본 뒤 구현한다.
- 스포크끼리 import 하지 않는다. 이 계획은 `hub`·`visit` 을 바꾸지 않는다.
- API 계약(009 "⑥-2 앱이 기댈 API 계약")은 바뀌지 않는다 — 경로·응답 스키마·오류 코드 그대로. `variables`(`pet_visits` 포함)와 템플릿 대기 칸은 응답에 나가지 않는다(N12).
- 구독자는 업체를 부르지 않는다(N13·N14). 잠금 순서는 고객 행 → 방문 행 → 알림 행.
- 줄을 고치는 UPDATE 는 `status = 'scheduled'` 조건을 단다. `sending`·`accepted`·끝난 줄은 고치지 않는다.
- 로그에는 매장·종류·판·결과만. 업체 ID·번호·주소·반려 사유 본문을 찍지 않는다.
- 묶음을 통째로 예약·변경·취소하는 경로의 결과(줄 수·문안·시각·줄이 달린 방문)는 지금과 같아야 한다 — 기존 단위 1873·통합 487 이 고치지 않고 통과해야 한다(이 계획이 뜻을 바꾸는 테스트는 작업에 이름을 적은 것뿐).
- 커밋은 `feat/notification-6-1b` 브랜치에 작업마다 하나. 푸시·main 병합은 사용자가 요청할 때.
- 명령은 `infra/` 에서: 단위 `docker compose run --rm backend pytest <경로> -q -p no:cacheprovider`, 통합은 끝에 `-m integration`. 통합 테스트 두 세션을 동시에 돌리지 않는다.

## 이 계획이 정한 것 (설계가 맡긴 것과 설계에서 벗어난 것)

- 아이별 방문은 `variables["pet_visits"]` 에 `"101:7,102:8"`(pet_id:visit_id, pet_id 오름차순)로 적는다. 짝을 모르는 아이는 빠져 있다.
- **시각 변경에서는 옮길 수 없는 줄을 제자리에 두지 않고 지금처럼 취소한다**(설계 3.1 은 "제자리에 둔다"). 옮긴 방문은 새 시각의 같은 종류 줄을 그 방문에 달아야 하는데 방문·종류당 대기 줄은 하나라 자리를 비워야 한다. 해당하는 것은 `pet_visits` 가 없는 옛 줄과 옮길 방문에 재발송 줄이 있는 경우뿐이다. 취소·노쇼·되돌리기에서는 설계대로 제자리에 둔다.
- `change` 를 만들 때 옛 시각이 같은 `scheduled` 줄이 없으면 다른 대기 줄이 있어도(다른 옛 시각, 또는 `sending`) 자기 줄을 만든다.
- 묶음 빼기가 훑는 종류: 취소·노쇼 `(confirm, reminder, change, next_visit)`, 시각 변경 `(reminder, change)`, 되돌리기 `(next_visit,)`. `cancel` 은 훑지 않는다(통째 취소에서 첫 이벤트가 만든 취소 안내를 둘째 이벤트가 지우면 안 된다). 방문 ID 로 거두는 기존 `cancel_pending` 은 그대로 뒤따른다.

## Review Focus

1. 디스패처가 막 집은(`sending`) 묶음 줄에 빼기·더하기가 오면 — 줄은 그대로 나가고 방문 저장은 실패하지 않는다. → 작업 2(저장소), 작업 4.
2. 세 마리 묶음에서 두 마리를 한 명령으로 취소 — 리마인드는 남은 한 마리 이름으로, 그 아이 방문에 달린다. → 작업 4.
3. 한 마리만 다른 시각으로 옮겼다가 원래 시각으로 다시 옮김 — 원래 시각의 리마인드에 다시 들어가 두 이름으로 한 통. → 작업 3·4.
4. 대기 판이 걸린 채 연동 해제 뒤 재연동 — 첫 등록으로 돌아가 `pending`, 대기 칸은 비어 있다. → 작업 5.
5. 재발송으로 만든 묶음 줄(`requested_by_member_id` 있음, `variables` 복사본)에서 한 마리가 빠짐 — 같은 규칙으로 이름이 빠진다. → 작업 4.

## File Structure

| 파일 | 일 |
|---|---|
| 만듦 `backend/apps/notification/domain/services/family_group.py` | 묶음 줄의 `pet_ids`·`pet_visits` 읽기와 빼기·더하기 계산(순수) |
| 고침 `…/app/services/message_text.py` | `message_pet_ids` 가 위 함수에 맡김 |
| 고침 `…/app/ports/output/message_repository.py`, `…/adapter/outbound/pg/message_pg_repository.py` | 묶음 `scheduled` 줄 찾기·고치기·하나 취소, `cancel_pending` 의 제외 목록 |
| 고침 `…/app/use_cases/handle_visit_event_interactor.py` | 더하기·빼기 |
| 고침 `…/domain/entities/notification_template.py`, `…/adapter/outbound/orm/notification_orm.py`, `…/mappers/notification_mapper.py` | 대기 칸 둘 |
| 만듦 `backend/alembic/versions/0013_notification_template_pending.py` | 칸 둘 + CHECK |
| 고침 `…/app/ports/output/template_repository.py`, `…/pg/template_pg_repository.py`, `…/app/ports/output/notification_queue_repository.py` | `upsert` 갈래, `decide_pending`, 심사 중 목록 |
| 고침 `…/app/services/template_registration.py`, `…/app/services/dispatcher.py`, `backend/scripts/reregister_templates.py` | 심사 결과 적기(공용), 고르는 기준 |
| 고침 `…/tests/helpers/fakes.py` | 스텁이 새 포트를 따라감 |
| 고침 `_docs/decisions/009-notification.md`, `…/domain/services/templates.py`(머리말) | 문서 |

---

### Task 0: 브랜치

- [ ] `git checkout -b feat/notification-6-1b` (main 의 bc2245d 위). 설계서·이 계획서를 `docs: ⑥-1b 알림톡 백엔드 보완 설계·계획` 으로 커밋한다.

---

### Task 1: 묶음 규칙 (순수 함수)

**Files:**
- Create: `backend/apps/notification/domain/services/family_group.py`
- Modify: `backend/apps/notification/app/services/message_text.py` (`message_pet_ids`)
- Test: `backend/apps/notification/tests/domain/test_family_group.py`

**Interfaces — Produces:**

```python
PET_IDS, PET_VISITS = "pet_ids", "pet_visits"

def pet_ids_of(variables: Mapping[str, str], pet_id: int | None) -> list[int]
    """variables 의 pet_ids. 그 칸이 없으면(옛 줄) [pet_id], pet_id 도 없으면 []."""
def pet_visits_of(variables: Mapping[str, str]) -> dict[int, int]
    """"101:7,102:8" → {101: 7, 102: 8}. 칸이 없거나 비면 {}."""

@dataclass(frozen=True)
class GroupEdit:
    variables: dict[str, str]   # 고친 variables (다른 칸은 그대로)
    visit_id: int               # 줄이 달릴 방문
    pet_id: int | None
    emptied: bool               # 남는 아이가 없다 — 취소할 줄
    stranded: bool              # 줄이 달린 아이가 빠졌는데 옮길 방문을 모른다

def without_pets(message: NotificationMessage, leaving: Collection[int]) -> GroupEdit | None
    """leaving 의 아이를 뺀다. 줄의 아이와 겹치지 않으면 None."""
def with_pets(message: NotificationMessage, pet_ids: Collection[int], pet_id: int | None, visit_id: int) -> dict[str, str] | None
    """pet_ids 를 더하고(오름차순·중복 없음) pet_id 가 있으면 pet_visits 에 pet_id:visit_id 를 채운다. 바뀐 것이 없으면 None."""
```

`without_pets` 규칙: 남는 아이가 없으면 `emptied=True`(variables·visit_id·pet_id 는 원래 값). 남으면 `pet_ids`·`pet_visits` 에서 빠진 아이를 지우고, `message.pet_id` 가 빠진 아이면 남은 아이 가운데 `pet_visits` 에 짝이 있는 가장 작은 pet_id 의 방문으로 `visit_id`·`pet_id` 를 바꾼다. 그런 아이가 없으면 `visit_id`·`pet_id` 는 그대로이고 `stranded=True`.

- [ ] **Step 1: 테스트** — `message()` 빌더(`notification.tests.helpers.builders`)로 만든다.

```python
ROW = dict(visit_id=7, pet_id=101, variables={"starts_at": "S", "pet_ids": "101,102", "pet_visits": "101:7,102:8"})

def test_다른_아이가_빠지면_이름만_빠지고_줄은_제자리다():
    edit = without_pets(message(**ROW), {102})
    assert (edit.variables["pet_ids"], edit.variables["pet_visits"]) == ("101", "101:7")
    assert (edit.visit_id, edit.pet_id, edit.emptied, edit.stranded) == (7, 101, False, False)
    assert edit.variables["starts_at"] == "S"

def test_줄이_달린_아이가_빠지면_남은_아이의_방문으로_옮긴다():
    edit = without_pets(message(**ROW), {101})
    assert (edit.variables["pet_ids"], edit.visit_id, edit.pet_id, edit.stranded) == ("102", 8, 102, False)

def test_옮길_방문을_모르면_제자리에_두고_stranded_다():
    edit = without_pets(message(visit_id=7, pet_id=101, variables={"pet_ids": "101,102"}), {101})
    assert (edit.variables["pet_ids"], edit.visit_id, edit.pet_id, edit.stranded) == ("102", 7, 101, True)

def test_모두_빠지면_emptied_다():
    assert without_pets(message(**ROW), {101, 102}).emptied is True

def test_세_마리에서_둘이_빠지면_남은_하나로_옮긴다():
    row = message(visit_id=7, pet_id=101, variables={"pet_ids": "101,102,103", "pet_visits": "101:7,102:8,103:9"})
    edit = without_pets(row, {101, 102})
    assert (edit.variables["pet_ids"], edit.variables["pet_visits"], edit.visit_id, edit.pet_id) == ("103", "103:9", 9, 103)

def test_겹치는_아이가_없으면_None_이다():
    assert without_pets(message(**ROW), {999}) is None

def test_pet_ids_칸이_없는_옛_줄은_자기_아이_하나로_본다():
    assert without_pets(message(visit_id=7, pet_id=101, variables={}), {101}).emptied is True
    assert without_pets(message(visit_id=7, pet_id=None, variables={}), {101}) is None

def test_더하면_오름차순으로_들어가고_짝을_채운다():
    row = message(visit_id=8, pet_id=102, variables={"pet_ids": "102", "pet_visits": "102:8"})
    assert with_pets(row, {101}, 101, 7) == {"pet_ids": "101,102", "pet_visits": "101:7,102:8"}

def test_이미_있는_아이는_짝만_채운다():
    row = message(visit_id=7, pet_id=101, variables={"pet_ids": "101,102", "pet_visits": "101:7"})
    assert with_pets(row, {101, 102}, 102, 8)["pet_visits"] == "101:7,102:8"

def test_바뀔_것이_없으면_None_이다():
    assert with_pets(message(**ROW), {101, 102}, 102, 8) is None
    assert with_pets(message(**ROW), (), None, 9) is None
```

- [ ] **Step 2:** `pytest apps/notification/tests/domain/test_family_group.py` → ImportError 로 실패.
- [ ] **Step 3:** 구현. `message_text.message_pet_ids` 는 `pet_ids_of(message.variables, message.pet_id)` 를 돌려주게 바꾼다(동작 같음).
- [ ] **Step 4:** 위 파일과 `apps/notification/tests/app` 전체 통과. `lint-imports` 6 kept(도메인은 app 을 import 하지 않는다).
- [ ] **Step 5:** 커밋 `feat(notification): 가족 묶음 줄의 아이 빼기·더하기 규칙(순수 함수)`

---

### Task 2: 저장소 — 묶음의 scheduled 줄 찾기·고치기

**Files:**
- Modify: `…/app/ports/output/message_repository.py`, `…/adapter/outbound/pg/message_pg_repository.py`, `…/tests/helpers/fakes.py`(`FakeMessages`)
- Test: `…/tests/adapter/test_notification_pg_repositories.py`(통합), `…/tests/test_fakes.py`

**Interfaces — Produces (`MessageRepository`):**

```python
async def list_scheduled_for_group(
    self, ctx: ShopContext, customer_id: int, starts_at_iso: str, kinds: Iterable[str]
) -> list[NotificationMessage]
    """같은 보호자·같은 variables.starts_at·넘긴 종류의 scheduled 줄, id 순. 행을 잠근다(FOR UPDATE)."""

async def rewrite_scheduled(
    self, ctx: ShopContext, message_id: int, variables: Mapping[str, str], visit_id: int, pet_id: int | None
) -> bool
    """scheduled 일 때만 variables·visit_id·pet_id 를 바꾼다. 바꿨으면 True. 옮길 방문에 같은 종류의 대기 줄이 있으면
    MessageAlreadyPendingError — create 처럼 세이브포인트 안이라 트랜잭션은 계속 쓸 수 있다."""

async def cancel_scheduled(self, ctx: ShopContext, message_id: int, reason: str) -> bool
    """scheduled 일 때만 canceled 로. 바꿨으면 True."""

async def cancel_pending(self, ctx, reason, visit_id=None, kinds=None, except_ids: Iterable[int] = ()) -> int
    """(기존) + except_ids 의 줄은 건드리지 않는다."""
```

- [ ] **Step 1: 통합 테스트**(같은 파일의 기존 `new_message`·`A`·`B` 를 쓴다) — 이름과 단언:
  - `test_묶음의_scheduled_줄은_같은_고객_시각_종류만_id_순으로_준다`: 매장 A 에 (고객 1, reminder, starts_at S) 둘(방문 7·8 — 둘째는 첫째를 취소한 뒤가 아니라 다른 방문), (고객 1, confirm, S), (고객 2, reminder, S), (고객 1, reminder, 다른 시각), `sending` 으로 집힌 줄 하나, 매장 B 의 같은 모양 하나 → `kinds=(REMINDER,)` 결과가 앞의 둘뿐이고 id 오름차순.
  - `test_rewrite_scheduled_는_variables_방문_아이를_바꾸고_다른_칸은_그대로다`: 바꾼 뒤 `get` 이 새 값, `scheduled_at`·`kind`·`status` 그대로, 반환 True.
  - `test_집힌_줄은_rewrite_도_cancel_scheduled_도_건드리지_않는다`(Review Focus 1): `claim_due` 뒤 둘 다 False, 줄은 `sending` 에 옛 값.
  - `test_옮길_방문에_같은_종류_대기_줄이_있으면_MessageAlreadyPendingError_이고_트랜잭션은_계속_쓸_수_있다`: 방문 7·8 에 reminder 대기 줄, 7 의 줄을 `visit_id=8` 로 → 예외, 뒤이은 `create`(다른 종류) 성공.
  - `test_다른_매장_컨텍스트로는_rewrite_도_cancel_scheduled_도_False_다`.
  - `test_cancel_pending_은_except_ids_의_줄을_남긴다`.
- [ ] **Step 2:** `pytest apps/notification/tests/adapter/test_notification_pg_repositories.py -m integration` → 새 테스트가 AttributeError 로 실패.
- [ ] **Step 3:** 포트·pg 구현. `list_scheduled_for_group` 은 `has_pending_for_group` 과 같은 조건에 `status == SCHEDULED`·`kind IN`·`with_for_update()`.
- [ ] **Step 4:** `FakeMessages` 에 같은 넷을 구현한다(`rewrite_scheduled` 는 같은 방문·종류의 다른 대기 줄이 있으면 `MessageAlreadyPendingError`, journal 에 `("rewrite_scheduled", id)`·`("cancel_scheduled", id, reason)`). `test_fakes.py` 에 스텁의 충돌·`scheduled` 조건 테스트 둘. `test_fakes_are_ports.py` 통과.
- [ ] **Step 5:** 통합·단위 통과. 커밋 `feat(notification): 묶음의 scheduled 줄을 찾아 고치는 저장소 메서드`

---

### Task 3: 구독자 — 더하기와 방문 짝 적기

**Files:**
- Modify: `…/app/use_cases/handle_visit_event_interactor.py` (`_create_for_group`, `_create`, 클래스 문서)
- Test: `…/tests/app/use_cases/test_handle_visit_event_interactor.py`

**Interfaces:** Consumes Task 1 `with_pets`·`PET_VISITS`, Task 2 `list_scheduled_for_group`·`rewrite_scheduled`.

`_create` 는 `variables["pet_visits"]` 에 `"{pet_id}:{visit_id}"`(아이가 없으면 `""`)를 넣는다.

`_create_for_group(ctx, event, kind, scheduled_at, **variables)` 의 새 순서:

1. `rows = list_scheduled_for_group(ctx, event.customer_id, _iso(event.starts_at), (kind,))`. `kind == CHANGE` 면 `variables.previous_starts_at` 이 같은 줄만 남긴다.
2. `rows` 가 비었으면 — `kind != CHANGE` 이고 `has_pending_for_group` 이 참이면(`sending` 줄) 지금처럼 건너뛴다. 아니면 `_create`.
3. `rows` 가 있으면 `pet_id` 가 있는 첫 줄이 받는 줄이다. 없으면(보호자만의 방문에 달린 줄) 건너뛴다. 있으면 `with_pets(받는 줄, event.family_pet_ids or 자기 pet_id, event.pet_id, event.visit_id)` 가 None 이 아닐 때 `rewrite_scheduled(…, visit_id=받는 줄.visit_id, pet_id=받는 줄.pet_id)`.

- [ ] **Step 1: 테스트**(`_World`·`_event`·`_pair` 를 쓴다)
  - `test_묶음의_둘째_이벤트는_방문_짝을_채운다`: `_pair(VisitReserved)` 뒤 `world.only(REMINDER).variables["pet_visits"] == "101:7,102:8"`, `pet_ids == "101,102"`, 줄은 방문 7.
  - `test_나중에_같은_시각에_따로_예약한_아이는_대기_중인_reminder_에_이름이_더해진다`: 101(방문 7, family (101,)) 예약 → `confirm` 을 `SENT` 로 바꿈 → 102(방문 8, family (102,)) 예약. reminder 한 줄, 방문 7, `pet_ids == "101,102"`. 방문 8 의 대기 줄은 `[(CONFIRM, NOW)]` 뿐(자기 접수 안내).
  - `test_다른_시각에서_옮겨_온_아이는_reminder_에_더해지고_change_는_따로_한_통이다`: 101·102 묶음을 `previous_starts_at=kst(10,15,14)` 로 STARTS 에 옮긴 change 대기 줄이 있는 상태에서, 103(방문 9)이 `previous_starts_at=kst(10,17,14)` 로 STARTS 에 옴 → reminder `pet_ids == "101,102,103"`, change 줄은 둘(방문 7 `"101,102"`, 방문 9 `"103"`).
  - `test_옛_시각이_같은_change_에는_더한다`: 위와 같되 103 의 옛 시각이 같으면 change 한 줄 `"101,102,103"`.
  - `test_보호자만의_방문에_달린_줄에는_더하지_않는다`: `pet_id=None` 방문 7 예약 뒤 101(방문 8) 예약 → reminder 한 줄, 방문 7, `pet_ids == ""`.
  - `test_보호자만의_방문이_아이_묶음에_오면_아무것도_바꾸지_않는다`: 반대 순서 → reminder `pet_ids == "101"`.
  - `test_sending_중인_묶음_줄에는_더하지_않고_건너뛴다`(Review Focus 1): reminder 를 `SENDING` 으로 바꾼 뒤 102 예약 → reminder 줄 하나 그대로 `"101"`.
  - `test_옮겼다가_원래_시각으로_돌아오면_다시_한_통에_들어간다`(Review Focus 3, 더하기 절반): reminder(방문 7, `"101"`, STARTS)만 있는 상태에서 102 가 `VisitRescheduled(starts_at=STARTS, previous_starts_at=MOVED)` → `"101,102"`.
- [ ] **Step 2:** 실패 확인.
- [ ] **Step 3:** 구현. 기존 테스트 가운데 `variables` 를 통째로 비교하는 단언은 `pet_visits` 칸만큼만 고친다(뜻이 바뀌는 기존 테스트는 없다 — 있으면 멈추고 보고).
- [ ] **Step 4:** 파일 전체 통과. 변이: 3번의 `pet_id is not None` 조건을 지우면 `보호자만의_방문에_달린_줄` 테스트가 떨어지는지 한 번 확인하고 되돌린다.
- [ ] **Step 5:** 커밋 `feat(notification): 대기 중인 묶음 알림톡에 뒤늦게 온 아이를 더한다`

---

### Task 4: 구독자 — 빼기와 옮기기

**Files:** Task 3 과 같다.

**Interfaces:** Consumes Task 1 `without_pets`, Task 2 전부.

인터랙터에 `_leave_group(ctx, event, starts_at, reason, kinds, keep_stranded) -> list[int]`(제자리에 남긴 줄의 id)를 더한다.

```
leaving = event.family_pet_ids or (자기 pet_id,)   # 비면 [] 를 돌려주고 끝
for m in list_scheduled_for_group(ctx, event.customer_id, _iso(starts_at), kinds):
    edit = without_pets(m, leaving)
    None        → 넘어간다
    emptied     → cancel_scheduled(m.id, reason)
    stranded    → keep_stranded 면 rewrite(제자리) 하고 kept 에 넣는다. 아니면 cancel_scheduled(m.id, reason)
    그 밖        → rewrite(edit.visit_id, edit.pet_id). MessageAlreadyPendingError 면 stranded 와 같이 다룬다
                  (제자리 rewrite 는 variables 만 바꾸고 visit_id·pet_id 는 m 의 것)
    줄이 이 이벤트의 방문에 그대로 남았으면(m.visit_id == event.visit_id 이고 옮기지 않음) kept 에 넣는다
```

부르는 곳(각각 그 뒤의 기존 `cancel_pending(…, visit_id)` 에 `except_ids=kept` 를 넘긴다):

| 이벤트 | starts_at | reason | kinds | keep_stranded |
|---|---|---|---|---|
| `VisitCanceled` | `event.starts_at` | `visit_canceled` | `(CONFIRM, REMINDER, CHANGE, NEXT_VISIT)` | True |
| `VisitClosed` no_show | `event.starts_at` | `no_show` | 같음 | True |
| `VisitRescheduled` | `event.previous_starts_at` | `rescheduled` | `(REMINDER, CHANGE)` | **False** |
| `VisitReserved(revived=True)` | `event.starts_at` | `reverted` | `(NEXT_VISIT,)` | True |

- [ ] **Step 1: 테스트** — 설계 3.1 표의 아홉 줄을 한 줄씩(콩이=101·방문 7, 두부=102·방문 8, 리마인드는 방문 7 에 달림):
  - `test_둘_다_취소하면_reminder_는_제자리에서_취소되고_cancel_은_두_이름_한_통이다`: `world.rows(7)` 에 `(REMINDER, CANCELED, …, "visit_canceled")`, 방문 8 에는 reminder 줄이 없다, `world.only(CANCEL).variables["pet_ids"] == "101,102"`.
  - `test_둘_다_옮기면_옛_reminder_는_제자리에서_취소되고_새_줄은_한_통씩이다`: 옛 reminder 는 방문 7 에서 `rescheduled`, 새 reminder·change 는 방문 7 에 `"101,102"`.
  - `test_줄이_달린_아이만_취소하면_reminder_는_남은_아이의_방문으로_옮겨진다`: reminder `visit_id == 8`, `pet_id == 102`, `pet_ids == "102"`, `scheduled_at` 그대로. `world.pending(7) == [(CANCEL, NOW)]`.
  - `test_다른_아이만_취소하면_reminder_에서_그_이름만_빠진다`: 방문 7, `"101"`. (기존 `test_묶음_가운데_한_마리만_취소하면_…_묶음의_줄은_남는다` 에 `world.only(REMINDER).variables["pet_ids"] == "101"` 단언을 더한다.)
  - `test_한_마리만_옮기면_옛_시각_reminder_에서_빠지고_새_시각에_자기_reminder_가_생긴다`: STARTS 줄 `"101"`, MOVED 줄 방문 8 `"102"`, change 는 방문 8 `"102"`.
  - `test_옮겼다가_원래_시각으로_돌아오면_한_통_두_이름이다`(Review Focus 3): 위에 이어 102 를 STARTS 로 되옮김 → 대기 reminder 는 하나(`"101,102"`, 방문 7), MOVED 의 reminder 는 `rescheduled` 취소.
  - `test_함께_완료한_뒤_줄이_달린_아이만_되돌리면_next_visit_은_남은_아이로_옮겨진다`: `_pair(VisitClosed, outcome="completed", previous_completed_at=None)` → `VisitReserved(visit_id=7, pet_id=101, family_pet_ids=(101,), revived=True)` → next_visit `visit_id == 8`, `"102"`, 취소되지 않음.
  - `test_함께_완료한_뒤_다른_아이만_되돌리면_next_visit_에서_그_이름만_빠진다`.
  - `test_취소한_아이를_되돌리면_reminder_에_다시_들어간다`: 102 취소 → 102 `revived` → reminder `"101,102"`.
  - `test_세_마리에서_둘을_한_명령으로_취소하면_reminder_는_남은_하나의_방문에_달린다`(Review Focus 2): family `(101,102)` 로 방문 7·8 취소 이벤트 둘 → reminder 방문 9, `"103"`.
  - `test_세_마리가_한_마리씩_빠지면_마지막에_취소된다`.
  - `test_pet_visits_가_없는_옛_줄은_취소에서는_이름만_빼고_제자리다`: `world.messages` 에 `message(visit_id=7, pet_id=101, kind=REMINDER, variables={"starts_at": _iso(STARTS), "pet_ids": "101,102"})` 를 직접 넣고 101 취소 → 방문 7 에 `scheduled`, `"102"`.
  - `test_pet_visits_가_없는_옛_줄은_시각_변경에서는_지금처럼_취소된다`: 같은 줄에서 101 을 MOVED 로 → 옛 줄 `rescheduled` 취소, 방문 7 에 MOVED 의 새 reminder 가 생긴다(예외 없음).
  - `test_옮길_방문에_재발송_줄이_대기_중이면_취소에서는_제자리에_둔다`: 방문 8 에 `requested_by_member_id=11` 인 reminder 대기 줄을 넣고 101 취소 → 묶음 줄은 방문 7 에 `"102"` 로 남는다.
  - `test_재발송으로_만든_묶음_줄에서도_이름이_빠진다`(Review Focus 5): 묶음 reminder 를 `SENT` 로 바꾸고 같은 `variables` 의 `requested_by_member_id=11` 줄을 방문 7 에 넣은 뒤 102 취소 → 그 줄 `"101"`.
  - `test_sending_중인_묶음_줄은_다른_아이가_빠져도_그대로다`(Review Focus 1): reminder 를 `SENDING` 으로 → 102 취소 → `"101,102"`, `SENDING`.
  - `test_한_마리_방문과_보호자만의_방문은_지금과_같다`: 한 마리 예약·취소, `pet_id=None` 예약·취소의 `world.rows(7)` 이 이 작업 전과 같은 모양(reminder `visit_canceled`).
- [ ] **Step 2:** 실패 확인.
- [ ] **Step 3:** 구현. 클래스 문서의 가족 묶음 문단을 새 규칙으로 고친다.
- [ ] **Step 4:** 파일 전체 + `apps/notification/tests` 전체 통과. 변이 둘: (가) 시각 변경의 `keep_stranded=False` 를 True 로 → `옛_줄은_시각_변경에서는_지금처럼_취소된다` 가 떨어진다. (나) 취소의 kinds 에 `CANCEL` 을 더함 → `둘_다_취소하면_…_cancel_은_두_이름_한_통` 이 떨어진다. 확인하고 되돌린다.
- [ ] **Step 5:** 커밋 `fix(notification): 가족 묶음에서 한 마리만 취소·변경·되돌리면 아직 안 나간 알림톡이 남은 아이를 따라간다(I6)`

---

### Task 5: 템플릿 대기 칸 — 스키마와 저장소

**Files:**
- Create: `backend/alembic/versions/0013_notification_template_pending.py` (`revision = "0013"`, `down_revision = "0012"`)
- Modify: `…/domain/entities/notification_template.py`, `…/orm/notification_orm.py`, `…/mappers/notification_mapper.py`, `…/ports/output/template_repository.py`, `…/pg/template_pg_repository.py`, `…/ports/output/notification_queue_repository.py`, `…/pg/message_pg_repository.py`(`list_pending_templates`), `…/tests/helpers/fakes.py`
- Test: `…/tests/adapter/test_notification_pg_repositories.py`, `backend/tests/integration/test_notification_schema.py`, `…/tests/test_fakes.py`, `…/tests/domain/test_entities.py`

**Interfaces — Produces:**

- 칸: `pending_text_version SMALLINT NULL`, `pending_provider_template_id VARCHAR(100) NULL`. CHECK `ck_notification_templates_pending_pair`: `(pending_text_version IS NULL) = (pending_provider_template_id IS NULL)`. `downgrade` 는 CHECK 와 칸 둘을 지운다.
- `NotificationTemplate` 끝에 `pending_text_version: int | None = None`, `pending_provider_template_id: str | None = None`, 그리고

```python
@property
def under_review(self) -> bool            # status == pending 이거나 대기 칸이 차 있다
@property
def review_provider_template_id(self) -> str   # 대기 칸이 차 있으면 그 ID, 아니면 provider_template_id
```

- `TemplateRepository.upsert(ctx, kind, text_version, provider_template_id, requested_at)` — 시그니처 그대로, 뜻이 갈린다: 기존 줄이 `approved` 면 대기 칸 둘만 적고 나머지 칸은 그대로. 그 밖(없음·`pending`·`rejected`)은 지금처럼 덮고 대기 칸을 비운다.
- 새 메서드

```python
async def decide_pending(
    self, ctx: ShopContext, kind: str, approved: bool, rejected_reason: str | None, decided_at: datetime
) -> None
    """대기 판의 심사 결과. 승인이면 대기 판을 본 칸(text_version·provider_template_id)으로 올리고 decided_at 을 적고
    rejected_reason 을 비운다. 반려면 본 칸은 그대로 두고 rejected_reason 만 적는다. 어느 쪽이든 대기 칸을 비운다.
    status 는 건드리지 않는다. 대기 칸이 빈 줄에는 아무것도 하지 않는다."""
```

- `NotificationQueueRepository.list_pending_templates()` — `status == pending` 이거나 대기 칸이 찬 줄 전부, id 순(문서 문장도 고친다).

- [ ] **Step 1: 테스트**
  - 통합 `test_승인된_템플릿을_다시_upsert_하면_대기_칸에만_적힌다`: upsert → `set_status(APPROVED)` → `upsert(ctx, CONFIRM, 2, "TP-V2", later)` 뒤 `get` 이 `(status, text_version, provider_template_id, pending_text_version, pending_provider_template_id) == (APPROVED, 1, "TP-V1", 2, "TP-V2")`, `decided_at`·`requested_at` 은 첫 값.
  - 통합 `test_pending_이나_rejected_인_템플릿을_다시_upsert_하면_덮고_대기_칸은_빈다`(parametrize 둘) — 기존 `test_템플릿_upsert_는_…_pending_으로_되돌린다` 는 이 갈래로 남는다(승인 뒤 덮는 단언이 있으면 이 테스트로 옮긴다 — **뜻이 바뀌는 기존 테스트**).
  - 통합 `test_대기_판이_승인되면_본_칸으로_올라간다`: 결과 `(APPROVED, 2, "TP-V2", None, None)`, `decided_at == 넘긴 시각`, `rejected_reason is None`.
  - 통합 `test_대기_판이_반려되면_옛_판이_남고_사유만_적힌다`: `(APPROVED, 1, "TP-V1", None, None)`, `rejected_reason == "사유"`.
  - 통합 `test_대기_판이_걸린_채_다시_upsert_하면_대기_칸을_덮는다`: 3판 → `(1, "TP-V1", 3, "TP-V3")`.
  - 통합 `test_대기_칸이_빈_줄에_decide_pending_은_아무것도_하지_않는다`.
  - 통합 `test_해제_뒤_다시_등록하면_pending_이고_대기_칸은_비어_있다`(Review Focus 4): 대기 판이 걸린 줄 → `delete_all` → upsert → `(PENDING, 2, "TP-V2", None, None)`.
  - 통합 `test_심사_중_목록은_pending_과_대기_칸이_찬_줄이다`: 기존 `test_큐의_전_매장_조회는_…` 옆에, approved+대기 줄이 목록에 들고 approved 만인 줄은 빠진다.
  - 스키마 `test_템플릿_대기_칸은_둘이_함께_있거나_함께_없다`(`test_notification_schema.py`): `_constraint_def(db_engine, "ck_notification_templates_pending_pair")` 에 두 칸 이름이 있고, 한 칸만 채운 INSERT 가 `IntegrityError`.
  - 단위 `test_entities.py`: `under_review`·`review_provider_template_id` 네 경우(pending / approved / approved+대기 / rejected).
- [ ] **Step 2:** 실패 확인.
- [ ] **Step 3:** 마이그레이션·ORM·엔티티·매퍼·저장소 구현. `FakeTemplates.upsert`·`decide_pending`, `FakeMessages.list_pending_templates` 를 같은 뜻으로 고치고 `test_fakes.py` 에 스텁의 갈래 테스트 둘.
- [ ] **Step 4:** `pytest apps tests -m integration` 전체와 단위 전체 통과(`tests/test_schema_drift.py` 포함). import-linter 6 kept.
- [ ] **Step 5:** 커밋 `feat(notification): 템플릿에 승인 전 판 칸을 두고 승인된 줄은 재등록해도 덮지 않는다(0013)`

---

### Task 6: 심사 결과 적기 — 디스패처·스크립트·변수 이름 고정

**Files:**
- Modify: `…/app/services/template_registration.py`, `…/app/services/dispatcher.py`(`refresh_templates`), `backend/scripts/reregister_templates.py`, `…/domain/services/templates.py`(머리말)
- Test: `…/tests/app/services/test_template_registration.py`(새 파일), `…/tests/app/services/test_dispatcher.py`, `backend/tests/test_reregister_templates.py`, `…/tests/domain/test_templates.py`, `…/tests/adapter/test_get_notification_overview_router.py`

**Interfaces:** Consumes Task 5 전부. **Produces** (`template_registration.py`):

```python
async def record_template_state(
    templates: TemplateRepository, ctx: ShopContext, template: NotificationTemplate, state: TemplateState, now: datetime
) -> str | None
    """업체가 준 심사 상태를 적는다. 아직 심사 중이면 None. 첫 판이면 set_status 로 적고 "approved"/"rejected".
    대기 판이면 decide_pending 으로 적고 "approved"/"rejected_new_version"."""
```

(`TemplateState` 는 `gateway.template_state` 가 돌려주는 기존 타입이다 — `message_gateway_port.py` 의 이름을 그대로 쓴다.)

디스패처 `refresh_templates` 와 스크립트 `refresh_pending` 은 `gateway.template_state(t.review_provider_template_id)` 로 묻고 `record_template_state` 로 적는다. 디스패처는 결과가 `"rejected_new_version"` 이면 WARNING `"매장 %s 의 %s 템플릿 새 판(%s)이 반려됐습니다 — 옛 판으로 계속 보냅니다."`(매장·종류·판). 스크립트의 결과 글자는 `record_template_state` 의 값, None 이면 `"pending"`.

스크립트 `reregister` 의 건너뛰는 조건: `template.status != REJECTED and TEXT_VERSION in (template.text_version, template.pending_text_version)`.

- [ ] **Step 1: 테스트**
  - `test_template_registration.py`: 첫 판 승인·반려(`set_template_status` journal), 대기 판 승인(본 칸이 새 판)·반려(옛 판 유지, 사유), 아직 심사 중이면 None 이고 저장소를 부르지 않는다 — 다섯.
  - `test_dispatcher.py`:
    - `test_새_판이_심사_중이어도_옛_판의_업체_ID_로_보낸다`: `template(status=APPROVED, provider_template_id="TP-V1", pending_text_version=2, pending_provider_template_id="TP-V2")` 에서 `run_once` → 게이트웨이가 받은 `provider_template_id == "TP-V1"`, 줄은 `ACCEPTED`(미뤄지지 않음).
    - `test_대기_판은_대기_칸의_업체_ID_로_묻고_승인되면_다음_발송부터_새_ID_다`: `refresh_templates` 가 `template_state("TP-V2")` 를 부르고, 뒤이은 발송이 `"TP-V2"`.
    - `test_대기_판이_반려되면_옛_판으로_계속_보내고_WARNING_에_매장_종류_판만_남긴다`(caplog — 사유 글자와 업체 ID 가 로그에 없다).
    - `test_대기_판_조회가_실패하면_그대로_두고_다음_주기에_다시_묻는다`.
  - `test_reregister_templates.py`:
    - 기존 `test_판이_다르거나_…` 는 그대로 통과해야 한다. 더해서 `test_승인된_종류를_새_판으로_재등록하면_대기_칸에_적히고_status_는_approved_다`(코드 판을 2 로 monkeypatch).
    - `test_새_판이_이미_심사_중이면_다시_등록하지_않는다`.
    - `test_새_판이_반려된_뒤에는_다시_고른다`(본 칸 1, 대기 칸 빔, 코드 판 2 → registered).
    - `test_refresh_는_대기_판도_묻고_결과를_적는다`: 결과 `[(1, "confirm", "approved")]` / 반려면 `"rejected_new_version"`.
  - `test_templates.py` `test_문안의_변수_이름은_판을_올려도_바꾸지_않는다`: 종류별 본문(+버튼) 변수 이름 집합이 아래와 같다. 실패 메시지는 `"변수 이름을 바꾸면 심사 중 옛 판 발송이 깨진다 — 설계 2026-11-10 3.2"`.

    ```python
    {CONFIRM: {"매장명", "대상", "일시"}, REMINDER: {"매장명", "대상", "일시"},
     REPORT: {"매장명", "대상", "기간안내", "링크"}, CHANGE: {"매장명", "대상", "이전일시", "일시"},
     CANCEL: {"매장명", "대상", "일시"}, NEXT_VISIT: {"매장명", "대상", "지난일", "간격"}}
    ```

  - `test_get_notification_overview_router.py` `test_overview_에_대기_칸은_나가지_않는다`: 대기 판이 걸린 템플릿이 있을 때 응답 `templates[0]` 의 키가 `{"kind", "status", "rejected_reason", "requested_at", "decided_at"}` 이고 `status == "approved"`.
- [ ] **Step 2:** 실패 확인.
- [ ] **Step 3:** 구현. `templates.py` 머리말에 한 문단: 판을 올릴 때 변수 이름 집합은 바꾸지 않는다(심사 중엔 옛 문안에 지금 코드의 변수 값을 채워 보낸다), 문자용 문안은 새 문안이 바로 나간다. 스크립트 머리말의 고르는 기준 문장도 고친다.
- [ ] **Step 4:** 단위 전체 통과. 변이: 디스패처가 `review_provider_template_id` 대신 `provider_template_id` 로 묻게 하면 `대기_판은_대기_칸의_업체_ID_로_묻고…` 가 떨어지는지 확인하고 되돌린다.
- [ ] **Step 5:** 커밋 `fix(notification): 새 판 심사 중에는 옛 판으로 계속 보내고 승인되면 올린다(I7)`

---

### Task 7: 통합 흐름·문서·전체 검증

**Files:**
- Test: `backend/tests/integration/test_notification_review_focus_wiring.py`(기존 도우미 `_shop`·`_booked`·`_transition`·`_rows`·`_run_once`·`_targets` 를 쓴다)
- Modify: `_docs/decisions/009-notification.md`

- [ ] **Step 1: 통합 테스트**
  - `test_묶음에서_줄이_달린_아이만_취소하면_reminder_는_남은_아이_이름으로_그_아이_방문의_내역에_있다`: 두 마리 예약 → `_run_once`(confirm 나감) → 콩이만 `customer_request` 취소 → `GET /v1/shops/{shop_id}/visits/{dubu}/notifications` 에 `reminder`/`scheduled` 한 줄, 콩이 방문의 내역에 대기 중인 reminder 없음 → 리마인드 시각 뒤의 `now` 로 `_run_once` → `_targets(gateway, "reminder") == ["두부"]`.
  - `test_나중에_같은_시각에_따로_예약한_아이도_reminder_한_통에_실린다`: 콩이 예약 → `_run_once` → 두부를 같은 시각에 따로 예약 → 리마인드 시각에 `_run_once` → `_targets(gateway, "reminder") == ["콩이·두부"]`, reminder 발송은 한 건.
  - `test_승인된_종류를_새_판으로_재등록해도_심사_중에는_옛_판으로_나가고_승인_뒤에는_새_판으로_나간다`: 연동·승인 → 저장소로 `upsert(ctx, "confirm", 2, "tpl-new", now)` → 예약 등록 → confirm 줄이 생기고 `_run_once` 가 옛 업체 ID 로 보냄 → `decide_pending(approved=True)` → 다음 예약의 confirm 은 `"tpl-new"`.
- [ ] **Step 2:** 실패했다가(작업 3~6 을 되돌린 것이 아니라, 테스트만 먼저 써서 도우미·단언 오타를 잡는다) 통과하는 것을 본다. 이미 구현이 있어 처음부터 통과하면 판별력을 변이 하나로 본다 — `_leave_group` 호출을 주석 처리하면 첫 테스트가 떨어진다.
- [ ] **Step 3: 009 고치기**
  - "알려진 동작"의 가족 묶음 항을 새 규칙으로 바꾼다(빼기·더하기·옮기기, 시각 변경에서 옮길 수 없는 줄은 취소, 보호자만의 방문이 섞인 묶음은 먼저 온 방문 이름으로 한 통이고 그 방문을 취소하면 함께 거둔다, `sending` 줄은 그대로).
  - "남는 것"의 I7 항을 고친 내용으로 바꾼다(대기 칸, 변수 이름 고정 제약, 새 판이 반려되면 `status: approved` 에 `rejected_reason`).
  - "⑥-2 앱이 기댈 API 계약"의 가족 묶음 문단에 더한다: 한 마리가 빠지면 대기 중인 묶음 줄이 남은 아이의 방문 내역으로 옮겨진다. overview 의 `rejected_reason` 은 `status` 가 `approved` 일 때도 찰 수 있고 앱은 `status` 로만 문구를 고른다.
  - "이 계획이 정한 것" 넷을 "⑥-1b 에서 정한 것" 절로 옮겨 적는다. 마이그레이션 0013 을 적는다.
- [ ] **Step 4: 전체 검증** (`infra/` 에서, 결과 숫자를 적는다)
  - `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"` — 1873 + 새 테스트, 실패 0.
  - `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration` — 487 + 새 테스트, 실패 0.
  - `docker compose run --rm --no-deps backend lint-imports --config .importlinter` — 6 kept.
  - `docker compose run --rm --no-deps auth python scripts/print_routes.py` — 80줄, main 과 diff 없음.
  - 개발 DB 에 0013 을 올린다(`_docs/harness.md` 의 마이그레이션 명령 — 칸 추가만이다). `backend` 를 이 브랜치 코드로 다시 띄운 뒤 `bash ../backend/scripts/check_notification_flow.sh` — 53줄 통과.
- [ ] **Step 5:** 커밋 `test(notification): 묶음에서 한 마리 취소·뒤늦은 예약·새 판 심사 중 발송을 실제 DB 로 고정` + `docs: 결정 기록 009 — ⑥-1b 가족 묶음·문안 판 올림`
