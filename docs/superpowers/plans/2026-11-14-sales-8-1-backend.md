# ⑧-1 매출 통계 백엔드 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 사장이 기간(일·주·월·연)의 매출 요약, 그 요약에서 이어지는 방문 목록, 다시 올 때가 지난 아이, 월 목표를 읽고 정하는 API 를 만든다.

**Architecture:** 새 스포크 없이 `visit` 스포크에 읽기 슬라이스 넷과 쓰기 슬라이스 하나를 더한다. 기간·비교 창 계산은 순수 도메인 서비스(`sales_period`)가, 집계는 새 출력 포트 `SalesRepository`(pg 구현이 SQL 로 그때그때 센다 — 캐시·미리 계산한 표 없음)가, 조립과 낱말의 뜻(조정·미선택·처음/다시·얼굴 거르기)은 인터랙터가 맡는다. 아이의 이름은 허브 포트 `CustomerDirectoryPort.briefs`, 사진은 아이의 프로필 사진(가장 최근 대표)을 `MediaLibraryPort` 로 읽는다.

**Tech Stack:** Python 3.13 · FastAPI · SQLAlchemy 2.0(asyncio) · Alembic · PostgreSQL · pytest

**Spec:** `docs/superpowers/specs/2026-11-14-sales-design.md`(3.1 낱말의 뜻, 3.3, 3.5, 4.1, 5, 7). 스포크 규칙은 `backend/apps/visit/_docs/CLAUDE.md`, 구조 규칙은 `_docs/architecture.md`.

## Global Constraints

- 브랜치 `feat/sales-8-1-backend`(main 에서). 첫 커밋에 설계서와 이 계획서를 넣는다. 커밋 메시지·주석·테스트 이름은 한국어, 커밋 끝에 `Co-Authored-By: Claude Fable 5.2 <noreply@anthropic.com>`. 푸시·main 병합은 사용자가 말할 때만.
- 과금·외부 연결 없음. 앱·웹 코드는 바꾸지 않는다.
- 경로는 모두 `/v1/shops/{shop_id}/sales/…` 이고 **`require_permission("sales:read")`** 다(목표 쓰기도). 저장소 메서드는 `ShopContext` 를 첫 인자로 받는다. 다른 스포크를 import 하지 않는다(허브 포트만).
- 슬라이스는 1:1 이다 — 라우터·프로바이더·인터랙터·입력 포트·DTO·스키마. 응답 스키마는 칸을 하나하나 적는다.
- **날짜는 매장 시간대로만 자른다**(`ctx.timezone`). SQL 은 `(starts_at AT TIME ZONE :tz)::date`. 금액은 정수(원).
- 매출 = 완료 방문(`status = 'completed'`)의 `visit_records.total_amount`(NULL 이 아닌 것)의 합. 총액이 NULL 인 완료 방문은 "금액을 적지 않은 것"으로 따로 센다(기록 자체가 없는 완료 방문도 여기에 든다).
- 받는 범위: `span ∈ {day, week, month, year}`, `anchor` 는 `2000-01-01`~`2100-12-31`(밖이면 422), `menu_id`·ID 류는 1~2^63-1, `cursor` 는 200자까지.
- 금액·이름·사진 주소를 로그에 남기지 않는다. 새 로그를 더하지 않는다.
- 검증 명령(모두 `infra/` 에서): 단위 `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"` · 통합 `… -m integration` · `docker compose run --rm --no-deps backend lint-imports --config .importlinter` · `docker compose run --rm --no-deps auth python scripts/print_routes.py`.

## Review Focus

1. **자정과 시간대** — 서울 23:30 에 시작한 방문은 그날의 것이고(UTC 로는 같은 날 14:30), 서울 00:10 에 시작한 방문은 UTC 로 전날이지만 그날의 것이다. 월·연의 첫날·끝날 경계도 같다. → 작업 3 의 실제 DB 테스트.
2. **진행 중 기간의 비교 창** — 3월 31일에 보는 3월은 2월 1일~끝(28·29일)과, 2월 29일에 보는 연은 작년 1월 1일~2월 28일과, 해를 걸친 주(12월 29일~1월 4일)는 그 앞 주와 견준다. 지난 기간은 앞 기간 전체와. → 작업 1.
3. **익명화·삭제한 아이** — 매출·방문 수·아이 수에는 남고, 이름·사진이 드는 곳(얼굴·단골·메뉴의 아이·칸의 아이들·방문 목록의 이름·다시 올 때가 지난 아이)에서는 빠진다. `briefs` 에 없는 `pet_id`(삭제)도 같다. → 작업 4·5·6.
4. **모자란 기록** — 기록이 없는 완료 방문, 총액만 있고 항목이 없는 기록, 항목 합이 총액보다 큰 기록(조정이 음수), 결제 수단이 NULL, 총액 0원. 합은 늘 맞는다: 결제 수단 합 = 메뉴 합 + 조정 = 칸의 합 = 매출. → 작업 3·4.
5. **범위 끝 입력** — `anchor=2100-12-31` 의 주·연, `anchor=2000-01-01` 의 앞 기간(1999년 — 계산은 되고 빈 값), 앞날의 기간(빈 요약, 오류 아님), 조작한 `cursor`, `filter=menu` 인데 `menu_id` 가 없음, 남의 매장 `menu_id`(빈 목록). 어느 것도 500 이 아니다. → 작업 1·5·7.

---

## 파일 구조 (`backend/apps/visit/` 아래)

| 파일 | 책임 |
|---|---|
| `domain/services/sales_period.py` | 기간·앞 기간·비교 창·칸(순수 함수) |
| `domain/value_objects/sales.py` | 집계 결과의 값 객체(`SalesTotals` 등) |
| `app/ports/output/sales_repository.py` · `adapter/outbound/pg/sales_pg_repository.py` | 집계 조회 |
| `app/ports/output/sales_goal_repository.py` · `adapter/outbound/pg/sales_goal_pg_repository.py` | 월 목표(설정 행의 칸) |
| `app/services/pet_cards.py` | 아이 ID 들 → 이름·사진 주소(익명화·삭제 거르기) |
| 슬라이스 다섯: `get_sales_summary` · `list_sales_visits` · `list_due_pets` · `get_sales_goal` · `update_sales_goal` | 라우터·프로바이더·인터랙터·입력 포트·DTO·스키마 |
| `backend/alembic/versions/0015_sales_goal.py` | `visit_shop_settings.sales_monthly_goal` |
| `backend/scripts/check_sales_flow.sh` | 게이트웨이 흐름 |

---

### Task 0: 브랜치와 문서

- [ ] `git checkout -b feat/sales-8-1-backend`, 설계서·계획서 커밋(`docs: ⑧ 매출 통계 설계와 ⑧-1 백엔드 계획`).

---

### Task 1: 기간과 비교 창 (순수 도메인)

**Files:**
- Create: `domain/services/sales_period.py`
- Test: `tests/domain/test_sales_period.py`

**Interfaces — Produces:**

```python
Span = Literal["day", "week", "month", "year"]
MIN_ANCHOR, MAX_ANCHOR = date(2000, 1, 1), date(2100, 12, 31)

@dataclass(frozen=True)
class Period:
    span: Span
    start: date          # 첫날
    end: date            # 끝날(포함)
    def contains(self, day: date) -> bool
    @property
    def until(self) -> date   # end + 1일 — SQL 의 반열린 끝

def period_of(span: Span, anchor: date) -> Period            # 주는 월요일~일요일
def previous_of(period: Period) -> Period                    # 어제·지난주·지난달·작년
def year_ago_of(period: Period) -> Period | None             # 연이면 None. 2월 29일 → 2월 28일
def elapsed_end(period: Period, today: date) -> date | None  # 진행 중이면 today, 지났으면 period.end, 앞날이면 None
def compare_window(period: Period, other: Period, today: date) -> tuple[date, date] | None
    # other 의 첫날부터 "같은 길이"의 끝날까지(포함). 지난 기간이면 other 전체. 앞날이면 None.
    # 같은 길이: 일·주 = 지난 날 수, 월 = 같은 날짜(그 달에 없으면 말일), 연 = 같은 월·일(2/29 → 2/28)
def bucket_keys(period: Period) -> list[date]                # 일: [], 주: 7일, 월: 그 달의 날들, 연: 열두 달의 1일
```

- [ ] **Step 1: 실패하는 테스트** — 값은 전부 손으로 적는다.

```python
@pytest.mark.parametrize("span,anchor,start,end", [
    ("day",   date(2026,11,14), date(2026,11,14), date(2026,11,14)),
    ("week",  date(2026,11,14), date(2026,11,9),  date(2026,11,15)),   # 토요일 → 월~일
    ("week",  date(2026,11,9),  date(2026,11,9),  date(2026,11,15)),   # 월요일 자신
    ("week",  date(2027,1,1),   date(2026,12,28), date(2027,1,3)),     # 해를 걸친 주
    ("month", date(2028,2,10),  date(2028,2,1),   date(2028,2,29)),    # 윤년
    ("month", date(2026,12,31), date(2026,12,1),  date(2026,12,31)),
    ("year",  date(2026,6,1),   date(2026,1,1),   date(2026,12,31)),
    ("year",  date(2100,12,31), date(2100,1,1),   date(2100,12,31)),
])
def test_기간의_첫날과_끝날(...)

def test_앞_기간은_어제_지난주_지난달_작년이다()       # 3월 → 2월, 1월 → 지난해 12월, 2000년 → 1999년
def test_작년_같은_기간은_윤일을_28일로_맞추고_연에는_없다()
@pytest.mark.parametrize(...)   # (기간, today) → (비교 시작, 비교 끝)
def test_진행_중인_기간은_같은_길이만큼만_견준다():
    # 11월 @ 11/14 → 10/1~10/14 · 3월 @ 3/31 → 2/1~2/28(2026) · 3월 @ 3/30 → 2/1~2/28
    # 이번 주 @ 수요일 → 지난주 월~수 · 오늘 → 어제 · 2028년 @ 2/29 → 2027/1/1~2/28
def test_지난_기간은_앞_기간_전체와_견준다()
def test_앞날의_기간은_견주지_않는다()                  # None, elapsed_end 도 None
def test_칸은_주_7일_월_그_달의_날수_연_12달이고_일에는_없다()
```

- [ ] **Step 2:** 실행 → 실패(모듈 없음). **Step 3:** 구현. **Step 4:** 통과. **Step 5:** 커밋 `feat(visit): 매출 기간과 비교 창 계산`.

---

### Task 2: 월 목표

**Files:**
- Create: `alembic/versions/0015_sales_goal.py`, `app/ports/output/sales_goal_repository.py`, `adapter/outbound/pg/sales_goal_pg_repository.py`, 슬라이스 `get_sales_goal`·`update_sales_goal`(라우터·프로바이더·인터랙터·입력 포트·DTO·스키마)
- Modify: `adapter/outbound/orm/visit_orm.py`(`VisitShopSettingsOrm.sales_monthly_goal`), `dependencies/visit_wiring.py`, `tests/helpers/fakes.py`
- Test: `tests/adapter/test_sales_goal_pg_repository.py`, `tests/adapter/test_get_sales_goal_router.py`, `tests/adapter/test_update_sales_goal_router.py`, `tests/app/test_sales_goal_interactors.py`

**Interfaces — Produces:**

```python
class SalesGoalRepository(ABC):
    async def get(self, ctx: ShopContext) -> int | None        # 설정 행이 없으면 None. 행을 만들지 않는다
    async def put(self, ctx: ShopContext, monthly_amount: int | None) -> int | None   # 설정 행이 있어야 한다(ScheduleRepository.ensure 뒤)
```

- 표: `visit_shop_settings.sales_monthly_goal INTEGER NULL`, CHECK `sales_monthly_goal IS NULL OR sales_monthly_goal BETWEEN 1 AND 100000000`. 새 표를 만들지 않는다(알림장 설정과 같은 방식).
- `GET /v1/shops/{shop_id}/sales/goal` → `{"monthly_amount": int | null}`.
- `PUT /v1/shops/{shop_id}/sales/goal` 본문 `{"monthly_amount": int | null}`(0 은 null 로 저장 — "목표 없음", 음수·1억 초과·소수·문자열 숫자는 422) → 같은 모양. 쓰기 인터랙터는 `ScheduleRepository.ensure` 로 설정 행을 만든 뒤 `put`.

- [ ] **Step 1: 실패하는 테스트**

```
pg:      설정 행이 없으면 None 이고 행을 만들지 않는다 / 정한 값을 다시 읽는다 / None 으로 지운다
         / 목표를 바꿔도 일정·알림장 설정은 그대로다 / 다른 매장의 목표는 보이지 않는다 / 범위 밖 값은 CHECK 가 막는다
라우터:  GET·PUT 모두 sales:read 가 없으면 403 PERMISSION_DENIED(직원) / 0 은 null 로 / 422 표(음수, 100000001, 1.5, "5", true, 본문 없음)
인터랙터: 쓰기는 설정 행을 먼저 만든다(ensure 호출 순서) / 0 → None
구조:    tests/integration/test_schema_drift 계열이 새 칸을 본다(ORM = 마이그레이션)
```

- [ ] **Step 2~4:** 실패 확인 → 구현 → 단위·통합 통과, 개발 DB `alembic upgrade head`(compose 의 backend 가 기동 때 올린다 — `docker compose restart backend` 뒤 `alembic current` 가 0015).
- [ ] **Step 5:** 커밋 `feat(visit): 매출 월 목표 — 0015, 읽기와 정하기`.

---

### Task 3: 집계 저장소 (실제 DB)

**Files:**
- Create: `domain/value_objects/sales.py`, `app/ports/output/sales_repository.py`, `adapter/outbound/pg/sales_pg_repository.py`
- Modify: `dependencies/visit_wiring.py`(`build_sales_repository`), `tests/helpers/fakes.py`(`FakeSalesRepository` — 포트 ABC 상속)
- Test: `tests/adapter/test_sales_pg_repository.py`(`pytestmark = pytest.mark.integration`)

**Interfaces — Produces** (`start`·`until` 은 매장 시간대의 날짜, `until` 은 끝 다음 날):

```python
@dataclass(frozen=True)
class SalesTotals:
    revenue: int; completed: int; priced: int; unrecorded: int; no_show: int; canceled: int
@dataclass(frozen=True)
class DaySales:      day: date; revenue: int; completed: int; pet_ids: tuple[int, ...]   # 그날 완료 방문의 아이(시작 순, 겹치지 않게, 5까지)
@dataclass(frozen=True)
class MenuSales:     menu_id: int; amount: int; count: int; latest_pet_id: int | None    # 그 메뉴를 가장 최근에 한 아이
@dataclass(frozen=True)
class PetVisits:     pet_id: int; visits: int; last_day: date; first_ever_day: date      # 기간 안의 완료 방문 수·마지막 날, 매장에서의 첫 완료 방문일
@dataclass(frozen=True)
class SalesVisitRow: visit_id: int; day: date; pet_id: int | None; customer_id: int; amount: int | None
@dataclass(frozen=True)
class DuePet:        pet_id: int; last_day: date
@dataclass(frozen=True)
class RemainingBookings: count: int; expected_amount: int | None

class SalesRepository(ABC):
    async def totals(self, ctx, start: date, until: date) -> SalesTotals
    async def by_day(self, ctx, start, until) -> list[DaySales]                 # 완료 방문이 있는 날만, 날짜순
    async def by_payment(self, ctx, start, until) -> dict[str | None, int]      # 총액이 있는 기록만. None = 미선택
    async def by_menu(self, ctx, start, until) -> list[MenuSales]               # 항목 합·건수, 금액 큰 순(같으면 menu_id)
    async def pets(self, ctx, start, until) -> list[PetVisits]                  # pet_id 가 있는 완료 방문
    async def remaining_reserved(self, ctx, now: datetime, until: date) -> RemainingBookings
        # now 이후·until 전의 reserved 수와, 그 예약들이 고른 메뉴의 정가(service_menus.price) 합. 정가가 있는 메뉴가 하나도 없으면 expected_amount 는 None
    async def report_counts(self, ctx, start, until) -> tuple[int, int]         # (알림장 줄이 있는 완료 방문 수, 그 가운데 연 적 있는 수)
    async def list_visits(self, ctx, start, until, kind: Literal["unrecorded","no_show","canceled","menu"],
                          menu_id: int | None, before: tuple[datetime, int] | None, limit: int) -> list[SalesVisitRow]
        # 시작 시각 최신순(같으면 visit_id 큰 순). limit+1 은 부르는 쪽이.
    async def due_candidates(self, ctx, today: date, now: datetime) -> list[DuePet]
        # 마지막 완료 방문일이 today-365 ~ today-57 이고 그 뒤(지금 이후) reserved 가 없는 아이. 오래된 순.
```

- 요일별·월별은 `by_day` 의 결과를 인터랙터가 접는다(질의를 더 만들지 않는다).
- [ ] **Step 1: 실패하는 테스트** — 방문·기록·항목·알림장 줄을 직접 넣는 도우미를 테스트 파일에 둔다(기존 `test_visit_pg_repository.py`·`test_report_pg_repository.py` 의 방식).

```
합계:   완료·총액 있는 것만 매출 / 기록 없는 완료와 총액 NULL 인 완료는 unrecorded / 0원은 priced 이고 unrecorded 가 아니다
        / 예약·미용 중·취소·노쇼는 매출에 없다 / no_show·canceled 는 그 기간의 것만 / 다른 매장은 0
경계:   서울 23:30 방문은 그날, 다음 날 00:10 방문은 다음 날(UTC 날짜와 다르다) / until 날의 00:00 방문은 빠진다
        / 2026-12-31 23:59 는 2026년, 2027-01-01 00:00 은 2027년                                       (Review Focus 1)
날짜별: 방문이 없는 날은 줄이 없다 / 아이는 시작 순으로 겹치지 않게 5까지 / 보호자만의 방문은 금액에는 들고 아이에는 없다
결제:   카드·현금·이체·None 으로 나뉘고 합이 매출과 같다
메뉴:   항목 합과 건수 / 총액 NULL 인 기록의 항목은 세지 않는다 / 가장 최근에 한 아이 / 보관한 메뉴도 나온다
아이:   기간 안의 방문 수와 마지막 날 / first_ever_day 는 기간 밖의 옛 방문도 본다(다시 온 아이) / 취소·노쇼는 첫 방문이 아니다
예약:   지금 이후의 reserved 만, until 전까지 / 예상 금액은 고른 메뉴의 정가 합(정가 없는 메뉴는 빼고, 하나도 없으면 None)
알림장: 줄이 있으면 보낸 것(끊은 줄·기간 지난 줄 포함) / 다시 보내 줄이 둘이어도 방문은 하나 / 하나라도 열었으면 연 것
목록:   종류 넷 / 최신순과 쪽 나눔(before) / 같은 시각의 둘이 쪽 경계에 걸려도 빠지거나 겹치지 않는다 / 남의 매장 menu_id 는 빈 목록
다시 올 때: 57일 전은 들고 56일 전은 아니다 / 365일 전은 들고 366일 전은 아니다 / 앞으로 예약이 있으면 빠진다
        / 지난 예약(reserved 인 채 지난 것)은 막지 않는다 / 마지막이 취소·노쇼면 그 앞의 완료 방문으로 본다 / 오래된 순
```

- [ ] **Step 2~4:** 실패 확인 → 구현 → 통과. **Step 5:** 커밋 `feat(visit): 매출 집계 저장소`.

---

### Task 4: 요약 슬라이스

**Files:**
- Create: `app/services/pet_cards.py`, 슬라이스 `get_sales_summary`(여섯 파일)
- Test: `tests/app/test_pet_cards.py`, `tests/app/test_get_sales_summary_interactor.py`, `tests/adapter/test_get_sales_summary_router.py`

**Interfaces:**
- Consumes: `sales_period` 전부, `SalesRepository`, `SalesGoalRepository`, `MenuRepository.list_by_ids`, `CustomerDirectoryPort.briefs`, `MediaLibraryPort.read_urls`, 아이의 프로필 사진 media_id 를 주는 기존 조회(허브 포트 `VisitLedgerPort.latest_covers` 의 구현이 쓰는 저장소 메서드 — 같은 스포크라 포트를 거치지 않고 그 저장소를 쓴다).
- Produces:

```python
# app/services/pet_cards.py
@dataclass(frozen=True)
class PetCard: pet_id: int; name: str; photo_url: str | None
async def pet_cards(ctx, pet_ids: Iterable[int], directory, covers, library) -> dict[int, PetCard]
    # briefs 에 없거나(삭제) 이름이 None(익명화)인 아이는 빠진다. 사진이 없으면 photo_url 은 None.
```

- `GET /v1/shops/{shop_id}/sales/summary?span=&anchor=` — `anchor` 가 없으면 매장 시간대의 오늘. 응답(칸 이름은 이대로):

```
span, period{start, end, elapsed_end|null}
revenue, visit_count, priced_count, average|null            # average = revenue // priced_count, priced_count 0 이면 null
compare{previous{start,end,revenue}|null, year_ago{start,end,revenue}|null}
    # previous 는 앞날의 기간이면 null. year_ago 는 연 보기·앞날이면 null, 그리고 작년 창의 매출이 0 이면 null
goal{monthly_amount}|null                                   # span=month 이고 기간이 오늘을 품고 목표가 있을 때만
pets{count, new_count, returning_count, faces[PetCard≤6], new[PetCard≤3], returning[PetCard≤4]}
    # faces 는 마지막 방문이 최근인 순(같으면 pet_id). new·returning 도 같은 순.
buckets[{key "YYYY-MM-DD"|"YYYY-MM", revenue, visit_count, future: bool, pets[PetCard≤5]}]
    # 주·월은 날마다(방문 없는 날도 0 으로), 연은 달마다(pets 는 빈 목록). 일은 빈 목록. future = 오늘 뒤
payments[{method "card"|"cash"|"transfer"|"none", amount}]  # 0원인 줄은 뺀다. 순서는 card, cash, transfer, none
menus[{menu_id|null, name, amount, count, pet: PetCard|null}]   # 금액순. 조정은 menu_id null·name "조정"·count 0·pet null, 차이가 0 이면 없다
regulars[{pet: PetCard, visit_count}]                        # 기간이 든 해(오늘까지)의 방문 수 큰 순 셋, 같으면 최근에 온 아이
bookings{remaining|null, expected_amount|null, no_show, canceled}   # remaining·expected_amount 는 기간이 오늘을 품을 때만. expected_amount 는 남은 예약의 정가 합(없으면 null)
weekdays[7 ints 월~일]|null                                  # span 이 month·year 일 때만
report{completed, sent, opened}|null                         # 완료 방문이 0 이면 null
unrecorded_count, due_pet_count
```

- [ ] **Step 1: 실패하는 테스트**(스텁 포트, 시각은 `now` 주입 — 2026-11-14 토요일 15:00 KST)

```
뜻:      평균은 원 단위에서 버린다 / priced 0 이면 평균 null / 조정 = 매출 − 항목 합(양수·음수·0 이면 줄 없음)
         / 미선택은 "none" 이고 0원인 수단은 줄이 없다 / 합: payments 합 = menus 합(조정 포함) = buckets 합 = revenue       (Review Focus 4)
아이:    처음 온 아이 = first_ever_day 가 기간 안 / new_count + returning_count = count / 얼굴은 최근 순 여섯
         / 익명화·삭제한 아이는 count 에는 들고 faces·new·returning·regulars·buckets.pets·menus.pet 에는 없다             (Review Focus 3)
         / 사진 없는 아이는 photo_url null 로 남는다
비교:    진행 중인 달은 같은 날까지의 지난달과 / 지난 달은 지난달 전체와 / 작년 창의 매출이 0 이면 year_ago 는 null
         / 연 보기에는 year_ago 가 없다 / 앞날의 기간은 compare 둘 다 null 이고 나머지는 0·빈 목록(오류 아님)
칸:      월은 그 달의 날수만큼(방문 없는 날 0) / 오늘 뒤는 future / 연은 열두 칸이고 달마다 합 / 일은 빈 목록
목표:    이번 달의 월 보기에만 / 지난 달·주·연에는 null / 목표가 없으면 null
그 밖:   weekdays 는 월·연에만 / remaining 은 진행 중인 기간에만 / report 는 완료 0 이면 null / 단골은 기간의 해 기준 셋
         / anchor 가 없으면 매장 시간대의 오늘(UTC 로는 어제인 시각으로 확인)
라우터:  sales:read 없으면 403 / span·anchor 의 422 표(span 없음·"quarter", anchor "2026-13-01"·"1999-12-31"·"2101-01-01"·"x")
         / anchor=2100-12-31&span=week·year 는 200 / anchor=2000-01-01 은 200 이고 previous 의 매출 0                    (Review Focus 5)
질의 수: 요약 한 번에 저장소 호출 수가 방문 수와 상관없다(스텁의 호출을 세어 고정)
```

- [ ] **Step 2~4:** 실패 확인 → 구현 → 통과. **Step 5:** 커밋 `feat(visit): 매출 요약`.

---

### Task 5: 방문 목록 슬라이스

**Files:** 슬라이스 `list_sales_visits`(여섯 파일), `domain/services/sales_cursor.py`(기존 `guardian_cursor` 와 같은 모양 — 시각+ID, 범위 넘침·깨짐은 `VisitInputError` 422)
**Test:** `tests/domain/test_sales_cursor.py`, `tests/app/test_list_sales_visits_interactor.py`, `tests/adapter/test_list_sales_visits_router.py`

- `GET /v1/shops/{shop_id}/sales/visits?span=&anchor=&filter=unrecorded|no_show|canceled|menu&menu_id=&cursor=` → `{"items": [{"visit_id", "date", "pet": PetCard|null, "amount": int|null}], "next_cursor": str|null}`, 20개씩.
- `filter=menu` 면 `menu_id` 필수(없으면 422), 다른 filter 에 `menu_id` 가 오면 무시한다. 익명화·삭제한 아이와 보호자만의 방문은 `pet: null` 로 남는다(방문은 보인다 — 금액을 채울 수 있어야 한다).

- [ ] 테스트: 종류 넷이 저장소에 그대로 넘어간다 / 다음 쪽 표시의 왕복 / 깨진·넘치는 cursor 422 / `filter=menu` 에 `menu_id` 없음 422 / 20개와 `next_cursor` / `pet` 거르기 / 403 / 앞날의 기간은 빈 목록. → 구현 → 커밋 `feat(visit): 매출에서 이어지는 방문 목록`.

---

### Task 6: 다시 올 때가 지난 아이 슬라이스

**Files:** 슬라이스 `list_due_pets`(여섯 파일), `domain/services/visit_cycle.py` 에 상수가 맞으면 거기, 아니면 `sales_period.py` 에 `DUE_AFTER_DAYS = 56`·`DUE_WITHIN_DAYS = 365`
**Test:** `tests/app/test_list_due_pets_interactor.py`, `tests/adapter/test_list_due_pets_router.py`

- `GET /v1/shops/{shop_id}/sales/due-pets?cursor=` → `{"items": [{"pet": PetCard, "last_visit_date": "YYYY-MM-DD"}], "next_cursor": str|null}`, 오래된 순 20개씩.
- 후보(`due_candidates`)를 다 읽고 `briefs` 로 거른 뒤(무지개다리·익명화·삭제 제외) 메모리에서 쪽을 나눈다 — 후보는 지난 한 해에 온 아이로 묶여 있다. `cursor` 는 `(last_day, pet_id)`. 요약의 `due_pet_count` 는 같은 거르기의 길이다(작업 4 가 이 함수를 쓰게 한다 — 거르기를 `app/services/due_pets.py` 한 곳에 둔다).

- [ ] 테스트: 무지개다리·익명화·삭제한 아이는 빠진다 / 오래된 순, 같은 날이면 pet_id 순 / 쪽 나눔과 cursor 왕복·깨진 cursor 422 / 요약의 수와 목록의 길이가 같다 / 403. → 구현 → 커밋 `feat(visit): 다시 올 때가 지난 아이`.

---

### Task 7: 배선·구조·흐름

**Files:**
- Modify: `backend/main.py`(라우터 다섯 등록), `backend/tests/integration/`(새 `test_sales_wiring.py`), 라우트 표 관련 테스트
- Create: `backend/scripts/check_sales_flow.sh`

- [ ] **Step 1: 통합 테스트**(실제 배선, 첫 줄은 테넌트 격리)

```
다른 매장의 사장은 403 NOT_A_MEMBER, 다른 매장의 방문은 요약에 섞이지 않는다
직원은 다섯 경로 모두 403 PERMISSION_DENIED
로그인 없이 401 — 로그인 없는 경로 목록(route_inspection)은 그대로다
방문 셋(카드 30,000 / 현금 50,000·항목 합 45,000 / 금액 없음)을 실제 API 로 만들고 요약을 읽는다:
  revenue 80000, visit_count 3, priced_count 2, average 40000, unrecorded_count 1, payments 합 = menus 합 = buckets 합 = 80000, 조정 5000
금액 없는 방문을 채우면 요약이 는다 / 방문을 취소하면 canceled 가 는다
익명화한 고객의 방문: 매출에는 남고 faces 에 없다
목표를 정하면 이번 달 요약에 보이고 지난 달 요약에는 없다
범위 끝: anchor=2100-12-31 주·연 200, 앞날의 달 200 빈 요약, 조작한 cursor 422, 큰 menu_id 422
응답 스키마의 칸 목록이 4번 작업의 표와 같다(칸이 늘거나 줄면 떨어진다)
```

- [ ] **Step 2:** 라우트 표 — `print_routes.py` 전후 비교(늘어난 줄은 `/sales/…` 다섯, 없어지거나 바뀐 줄 없음), `lint-imports` 6 kept.
- [ ] **Step 3:** `check_sales_flow.sh`(기존 `check_guardian_flow.sh` 의 틀 — `set -euo pipefail`, 본문은 변수로, 단계 이름과 판정만 찍는다): 매장·사장·직원·고객 둘 → 이번 달에 완료 방문 넷(결제 수단 셋 + 금액 없는 하나, 한 건은 항목 합 ≠ 총액)과 노쇼 하나, 지난달에 완료 방문 하나, 앞날의 예약 하나 → 요약(월)의 숫자를 손계산과 견준다(매출·방문 수·평균·결제 수단별·메뉴별·조정·처음/다시·노쇼·남은 예약·금액 없는 수·비교의 앞 기간 매출) → 주·일·연 요약의 매출 → 방문 목록 넷 → 목표 정하기·읽기·지우기 → 직원 403. 확인 25줄 안팎.
- [ ] **Step 4:** 단위·통합 전체, 기존 흐름 스크립트(`check_visit_flow.sh`·`check_report_flow.sh`·`check_guardian_flow.sh`) 그대로 통과.
- [ ] **Step 5:** 변이 — 날짜 자르기에서 시간대를 빼기, 총액 NULL 조건 빼기, 매장 조건 빼기, 익명화 거르기 빼기 — 각각 해당 테스트가 떨어지는 것을 본다.
- [ ] **Step 6:** 커밋 `feat(visit): 매출 경로 배선과 흐름 스크립트`.

---

### Task 8: 문서

- [ ] `backend/apps/visit/_docs/CLAUDE.md`(매출 단락 — 낱말의 뜻, 날짜 자르기, 집계는 읽을 때, 아이 사진은 프로필 사진, 익명화 거르기 자리), 루트 `CLAUDE.md`(명령어에 `check_sales_flow.sh`), `_docs/architecture.md`·`_docs/harness.md`, 새 결정 기록 `_docs/decisions/011-sales.md`(정한 것, 알려진 동작, 남는 것, **⑧-2·⑧-3 앱이 기댈 API 계약**, 검증 숫자).
- [ ] 마지막 전체 검증 뒤 커밋 `docs: ⑧-1 매출 통계 백엔드 — 스포크 규칙, 결정 기록 011`.
