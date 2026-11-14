# ③-B1 예약의 확인할 것·미용 동의·주의 고객 — 백엔드 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 살아 있는 방문과 아직 없는 예약에 대해 "확인할 것"을 사실에서 계산해 주고, 반려동물의 미용 동의 받은 날과 고객의 주의 표시를 쓰고 읽게 한다.

**Architecture:** 사실은 customer 가 갖는다(`pets`·`customers` 의 새 칸, 0016). 판정은 visit 의 순수 함수 연쇄(`visit/domain/chain/`)가 한다. visit 은 customer 의 사실을 허브 포트 `CustomerDirectoryPort.care_facts` 로 **한 번에** 읽고, 방문 쪽 사실(완료 이력·지난 1년 노쇼)은 새 저장소 포트 `VisitCheckRepository` 가 한 번에 센다. 조립은 `visit/app/services/visit_checks.py` 한 곳.

**Tech Stack:** Python 3.13 · FastAPI · SQLAlchemy 2.0 asyncio · Alembic · pytest

**Spec:** `docs/superpowers/specs/2026-11-14-visit-checks-design.md`. 규칙은 루트 `CLAUDE.md`, `backend/apps/customer/CLAUDE.md`, `backend/apps/visit/CLAUDE.md`, `_docs/architecture.md`.

## Global Constraints

- 브랜치 `feat/visit-3b1-backend`. 커밋·주석·테스트 이름은 한국어, 커밋 끝에 `Co-Authored-By: Claude Fable 5.2 <noreply@anthropic.com>`. 푸시·병합은 사용자가 말할 때만. 과금·외부 연결 없음. 앱·웹은 바꾸지 않는다.
- 스포크끼리 import 하지 않는다(허브 포트). 슬라이스 1:1(router·provider·interactor·input port·dto·schema). 매장 범위 저장소 메서드의 첫 인자는 `ShopContext`.
- 읽기는 `get_shop_context`, 동의·주의의 쓰기는 `require_permission("customer:write")`. 새 권한 없음. 적은 사람은 `ctx.member_id`.
- **막지 않는다** — 확인할 것은 어떤 쓰기도 거절하지 않는다. 기존 응답의 칸을 지우거나 뜻을 바꾸지 않는다(더하기만).
- 기준값(고정): 노령 10살 · 동의 유효 365일(365일째까지 유효) · 오랜만 180일 초과 · 노쇼는 방문 날 앞 365일 · 주의 표시 365일 · 사유 1~100자(앞뒤 공백을 뗀 뒤).
- 날짜는 전부 **매장 시간대**의 날이다. 판정의 기준일은 그 방문의 날(미리 보기는 받은 `date`).
- 주의 사유·지병 메모를 로그·오류 메시지에 남기지 않는다. 공개·보호자 경로와 스키마는 건드리지 않는다(`route_inspection` 허용 목록 불변).
- 잠금: 동의는 `PetRepository.lock_owner`, 주의는 `CustomerRepository.lock_active` 를 맨 앞에서.
- 검증(전부 `infra/` 에서): 단위 `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"` · 통합 `… -m integration` · `docker compose run --rm --no-deps backend lint-imports --config .importlinter` · 라우트 표 `docker compose run --rm --no-deps auth python scripts/print_routes.py`.

## Review Focus

1. **날짜의 끝** — 10번째 생일 당일(노령), 출생 연도만 있는 아이(올해 − 연도), 동의 365일째(유효)·366일째(기한 지남), 마지막 방문 180일(안 뜸)·181일(뜸), 노쇼 365일 앞(셈)·366일 앞(안 셈), 주의 `until` 당일(살아 있음)·다음 날(없음). 자정 앞뒤의 방문은 매장 시간대로 센다.
2. **지금 이 방문은 뺀다** — 방문 상세의 `first_visit`·`long_absence` 는 자기 자신과 같은 날 뒤의 방문을 이력으로 세지 않는다. 미용 중인 첫 방문도 `first_visit` 다.
3. **매장 경계와 익명화** — 다른 매장의 고객·아이 ID 로는 사실이 나오지 않는다. 익명화하면 주의 칸 넷·동의 칸 둘이 비고, 그 고객은 `care_facts` 에서 빠진다. 기한 지난 주의는 목록·상세·확인할 것 어디에도 없다.
4. **질의 수** — 하루 목록은 방문이 1개든 30개든 `care_facts` 한 번, `VisitCheckRepository` 의 두 메서드 한 번씩이다. 보호자만의 방문·아이가 섞인 날에도 같다.
5. **지병을 더하면 동의가 비고**, 빼거나 메모만 고치면 그대로다. 기타(custom_label)를 다른 기타로 바꾼 것도 더한 것으로 친다.

---

### Task 1: customer — 칸, 미용 동의, 주의 표시

**Files:** Create `backend/alembic/versions/0016_care_marks.py`, `customer/domain/services/care_marks.py`, 슬라이스 넷(`set_pet_grooming_consent`·`clear_pet_grooming_consent`·`set_customer_caution`·`clear_customer_caution` — 각각 router·provider·interactor·input port·dto, 스키마는 기존 상세 스키마를 돌려준다); Modify `customer/adapter/outbound/orm/customer_orm.py`, 엔티티 `Customer`·`Pet`, `CustomerRepository`·`PetRepository`(포트·PG·가짜), `update_pet_interactor.py`, 익명화, 상세·목록의 뷰·스키마·리더, `main.py`(라우터 등록), `tests/route_inspection.py` 의 프로세스별 목록; Test `customer/tests/domain/test_care_marks.py`, `customer/tests/app/test_grooming_consent.py`·`test_customer_caution.py`, 기존 익명화·수정·상세·목록 테스트에 추가

**Interfaces — Produces:**

```python
# 0016: pets.grooming_consent_on DATE NULL, pets.grooming_consent_by_member_id BIGINT NULL  (CHECK: 둘이 함께)
#       customers.caution_reason VARCHAR(100) NULL, caution_until DATE NULL, caution_set_at TIMESTAMPTZ NULL,
#       caution_set_by_member_id BIGINT NULL  (CHECK ck_customers_caution_all_or_none: 넷이 함께)
# customer/domain/services/care_marks.py  — 순수 함수
CAUTION_DAYS = 365; CONSENT_DAYS = 365; REASON_MAX = 100
def clean_reason(text: str) -> str                      # strip → 1~100자 아니면 CustomerInputError
def caution_until(today: date) -> date                  # today + 365일
def caution_active(until: date | None, today: date) -> bool   # until is not None and until >= today
def check_consent_day(received_on: date, today: date) -> None # 앞날이면 CustomerInputError
def conditions_added(before: Iterable[ConditionEntry], after: Iterable[ConditionEntry]) -> bool
    # (type_code, custom_label) 로 견줘 after 에만 있는 것이 하나라도 있으면 True
# 저장소
PetRepository.set_grooming_consent(ctx, pet_id, received_on: date | None, member_id: int | None) -> Pet
CustomerRepository.set_caution(ctx, customer_id, reason: str | None, until: date | None, set_at: datetime | None, member_id: int | None) -> Customer
# 엔티티의 새 칸: Pet.grooming_consent_on, Customer.caution_reason / caution_until
# 뷰·스키마에 더하는 칸
#   반려동물 상세: grooming_consent_on: date | null ; caution: {reason, until} | null   (보호자 탭이 이 응답으로 그린다)
#   고객 상세: caution: {reason, until} | null
#   고객 목록의 줄: caution: bool
# 경로 (전부 customer:write)
PUT    /v1/shops/{shop_id}/pets/{pet_id}/grooming-consent      body {received_on: date | null}  → PetDetailSchema
DELETE /v1/shops/{shop_id}/pets/{pet_id}/grooming-consent                                        → PetDetailSchema
PUT    /v1/shops/{shop_id}/customers/{customer_id}/caution     body {reason: str}               → 고객 상세 스키마
DELETE /v1/shops/{shop_id}/customers/{customer_id}/caution                                       → 고객 상세 스키마
```

- 살아 있지 않은 주의(기한 지남)는 응답에서 `null`/`false` 다 — 리더가 `caution_active(until, today)` 로 거른다. DB 의 칸은 그대로 둔다(다시 달면 덮인다).
- 주의를 다시 달면 `until = today + 365`, `set_at = now`, `set_by = ctx.member_id`. `DELETE` 는 넷을 비우고, 없던 것을 풀어도 200 이다(멱등).
- 동의 `received_on` 이 null 이면 오늘. `DELETE` 는 둘을 비운다(멱등). 무지개다리 아이에게도 적을 수 있다(막지 않는다).
- `update_pet` — 잠금 뒤 읽은 지병과 새 지병을 `conditions_added` 로 견줘 True 면 같은 트랜잭션에서 동의를 비운다.
- 익명화 — 고객의 주의 칸 넷과 그 고객 반려동물의 동의 칸 둘을 비운다.
- 주의·동의는 검색 줄(`rebuild_search_entry`)과 상관없다 — 다시 만들지 않는다.

- [ ] 테스트(도메인 경계값 → 유스케이스: 달기·다시 달기·풀기·멱등·다른 매장 404·익명화한 고객 404·직원도 됨·사유 0자·101자·공백뿐, 동의 오늘·지난 날·앞날 422·지우기, 지병 더하기/빼기/메모만, 익명화가 비움, 상세·목록의 칸과 기한 지난 주의) → 구현 → 단위 테스트·import-linter. 커밋 `feat(customer): 미용 동의 받은 날과 주의 표시 — 칸(0016), 쓰기 넷, 상세·목록`.

---

### Task 2: 허브 포트 `care_facts`, 방문 쪽 사실, 판정 연쇄

**Files:** Create `hub/app/dtos/care_facts.py`, `visit/domain/chain/__init__.py`·`visit_checks.py`, `visit/app/ports/output/visit_check_repository.py`, `visit/adapter/outbound/pg/visit_check_pg_repository.py`; Modify `hub/app/ports/customer_directory_port.py`, `customer/app/use_cases/customer_directory_interactor.py`(+ 필요한 저장소 읽기), visit 의 가짜 디렉터리·가짜 저장소(`visit/tests/helpers`), `dependencies/`; Test `visit/tests/domain/test_visit_checks.py`, `customer/tests/app/test_care_facts.py`, `visit/tests/adapter/test_visit_check_repository.py`(통합)

**Interfaces — Produces:**

```python
# hub/app/dtos/care_facts.py
@dataclass(frozen=True)
class CautionFact:   reason: str; until: date
@dataclass(frozen=True)
class ConditionFact: label: str; note: str | None
@dataclass(frozen=True)
class PetCareFact:
    pet_id: int; customer_id: int
    birth_date: date | None; birth_year: int | None
    conditions: tuple[ConditionFact, ...]        # 정렬은 종류의 sort_order
    consent_on: date | None; passed_away: bool
@dataclass(frozen=True)
class CareFacts:
    cautions: dict[int, CautionFact]             # 고객 ID → 살아 있는 주의만(today 기준)
    pets: dict[int, PetCareFact]                 # 익명화한 고객의 아이·다른 매장·없는 ID 는 빠진다
    known_customers: frozenset[int]              # 살아 있는(익명화하지 않은) 이 매장의 고객
# CustomerDirectoryPort
async def care_facts(self, ctx, customer_ids: tuple[int, ...], pet_ids: tuple[int, ...], today: date) -> CareFacts

# visit/app/ports/output/visit_check_repository.py
@dataclass(frozen=True)
class PetHistory: has_completed: bool; last_completed_on: date | None   # 매장 시간대의 날
class VisitCheckRepository(ABC):
    async def pet_histories(self, ctx, pet_ids: tuple[int, ...], before: dict[int, datetime]) -> dict[int, PetHistory]
        # before[pet_id] = 그 시각보다 **앞에 시작한** 완료 방문만 센다(자기 자신·뒤의 방문 제외). 없는 아이는 PetHistory(False, None)
    async def recent_no_shows(self, ctx, customer_ids: tuple[int, ...], since: dict[int, datetime], until: dict[int, datetime]) -> dict[int, int]
        # since <= starts_at < until 인 노쇼 방문 수. 0 이면 키가 없다

# visit/domain/chain/visit_checks.py  — 순수. 판정자 하나가 항목 하나를 내거나 넘긴다
SENIOR_AGE = 10; CONSENT_DAYS = 365; ABSENCE_DAYS = 180; NO_SHOW_DAYS = 365
@dataclass(frozen=True)
class CheckSubject:          # 방문 하나(또는 아직 없는 예약의 아이 하나)에 대한 사실
    on: date                 # 방문의 날(매장 시간대)
    pet: PetCareFact | None  # 보호자만의 방문이면 None
    caution: CautionFact | None
    no_show_count: int       # 지난 1년
    history: PetHistory | None
@dataclass(frozen=True)
class Check:
    code: str                # caution · no_show · first_visit · consent · conditions · long_absence
    scope: str               # "customer" | "pet"
    detail: dict             # 코드별 — 아래
def age_on(birth_date, birth_year, on: date) -> int | None
def checks_for(subject: CheckSubject) -> list[Check]        # 설계 3.1 의 순서
COUNTED = frozenset({"caution", "no_show", "first_visit", "consent", "long_absence"})   # conditions 는 세지 않는다
```

- `detail`: `caution {reason, until}` · `no_show {count}` · `first_visit {}` · `consent {reasons: ["senior"|"conditions"…], state: "missing"|"expired", received_on|None}` · `conditions {items: [{label, note}]}` · `long_absence {days, last_visit_on}`.
- 무지개다리 아이는 아이 쪽 항목이 없다. `pet` 이 None(보호자만·익명화로 빠짐)이면 보호자 항목만. 고객이 `known_customers` 에 없으면 조립 쪽이 빈 목록을 낸다(Task 3).
- `first_visit` 과 `long_absence` 는 함께 뜨지 않는다(이력이 없으면 첫 방문뿐).

- [ ] 테스트(Review Focus 1·2·5 의 경계값을 매개변수로, 항목의 순서, 무지개다리·보호자만, `care_facts` 의 매장 경계·익명화·기한 지난 주의·지병 이름과 순서, 통합: `before` 가 자기 자신을 빼는지·자정 앞뒤·노쇼 창의 양 끝·다른 매장) → 구현 → 단위·통합·import-linter. 커밋 `feat(visit): 확인할 것의 판정 연쇄와 사실 읽기 — care_facts 포트, 방문 이력·지난 1년 노쇼`.

---

### Task 3: visit — 미리 보기, 방문 상세, 하루 목록

**Files:** Create `visit/app/services/visit_checks.py`, 슬라이스 `get_visit_checks`(router·provider·interactor·input port·dto·schema); Modify `get_visit_interactor.py`·`get_visit_dto.py`·`get_visit_schema.py`, `list_day_visits_interactor.py`·dto·schema, `dependencies/`, `main.py`, `tests/route_inspection.py`; Test `visit/tests/app/test_visit_checks_service.py`·`test_get_visit_checks.py`, 기존 상세·하루 목록 테스트에 추가

**Interfaces — Consumes:** Task 2 의 `care_facts`·`VisitCheckRepository`·`checks_for`·`COUNTED`. **Produces:**

```python
# visit/app/services/visit_checks.py
@dataclass(frozen=True)
class CheckTarget: key: int; customer_id: int; pet_id: int | None; starts_at: datetime   # key 는 부르는 쪽의 식별자(visit_id 또는 순번)
async def read_checks(ctx, targets: list[CheckTarget], directory: CustomerDirectoryPort, repo: VisitCheckRepository, today: date) -> dict[int, list[Check]]
    # 포트 한 번 + 저장소 메서드 둘 한 번씩. targets 가 비면 아무것도 부르지 않는다.
# 경로
GET /v1/shops/{shop_id}/visit-checks?customer_id=&pet_ids=1,2&date=YYYY-MM-DD      (get_shop_context)
  → {customer: [CheckSchema], pets: [{pet_id, checks: [CheckSchema]}]}
  # pet_ids 는 0~10개. 비면 보호자 항목만. date 는 받는 범위 = 예약 범위(오늘 앞뒤 366일), 밖이면 422.
  # 이 매장에 없는·익명화한 고객이면 404 CUSTOMER_NOT_FOUND. 그 고객의 아이가 아닌 pet_id 는 빠진다(404 아님).
  # 기준 시각은 그 날의 끝(다음 날 0시) — 그날 앞서 끝낸 방문도 이력이다.
# 방문 상세 응답에 더하는 칸
checks: [CheckSchema]            # 살아 있는 방문(reserved·in_progress)만, 그 밖은 []
# 하루 목록의 항목에 더하는 칸
customer_check_count: int        # COUNTED 가운데 scope == customer
pet_check_count: int             # COUNTED 가운데 scope == pet
CheckSchema = {code, scope, + detail 의 칸을 펼쳐서}   # 코드마다 칸이 다르다 — 없는 칸은 싣지 않는다(exclude_none 이 아니라 코드별 스키마의 합)
```

- 상세·하루 목록의 기준 시각은 그 방문의 `starts_at`, 기준일은 그 날(매장 시간대).
- 하루 목록은 살아 있는 방문만 `CheckTarget` 으로 넘긴다. 완료·취소·노쇼 항목의 두 수는 0.
- 기존 `no_show_count`(전 기간)는 그대로 둔다.

- [ ] 테스트(조립: 호출 수 고정 — 방문 1개·30개·보호자만 섞임·빈 날, 가족 묶음의 보호자 항목, 익명화한 고객의 방문은 빈 목록; 미리 보기: 404·남의 아이 빠짐·`pet_ids` 11개 422·`date` 범위; 상세: 미용 중인 첫 방문·완료 방문은 `[]`; 하루 목록의 두 수와 `conditions` 를 세지 않음) → 구현 → 단위·통합·import-linter·라우트 표(늘어난 줄이 다섯인지). 커밋 `feat(visit): 확인할 것 — 미리 보기, 방문 상세, 하루 목록`.

---

### Task 4: 통합 배선·흐름 스크립트·문서

- [ ] `backend/tests/integration/test_visit_checks_wiring.py` — 실제 DB·실제 두 스포크로: 노령·지병 아이를 예약 → 상세에 `consent`·`conditions`·`first_visit`; 동의를 적으면 `consent` 가 사라짐; 지병을 더하면 다시 뜸; 주의를 달면 `caution`, 풀면 사라짐; 노쇼 하나 뒤 다음 예약에 `no_show`; 익명화 뒤 칸이 비었는지(DB 를 직접 읽는다); 직원 토큰으로 쓰기 넷.
- [ ] `backend/scripts/check_visit_checks_flow.sh` — 게이트웨이로 같은 흐름(기존 `check_sales_flow.sh` 의 꼴: `ok`/`fail` 줄, 본문은 변수로). 사유·전화번호를 찍지 않는다.
- [ ] 문서: `backend/apps/customer/CLAUDE.md`·`backend/apps/visit/CLAUDE.md`·`backend/apps/hub/CLAUDE.md`(포트 한 줄), 루트 `CLAUDE.md` 의 명령어, `_docs/harness.md`, `_docs/decisions/012-visit-checks.md`(정한 것 + **③-B2 앱이 기댈 API 계약** + 검증 숫자). 변이 셋(기준일을 오늘로, 자기 자신을 이력에 넣기, 기한 지난 주의 거르기 빼기)이 잡히는지 확인. 커밋.
