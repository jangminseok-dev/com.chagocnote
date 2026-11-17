# ⑭-1 반복 예약 백엔드 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** "N주마다 같은 요일·시각"의 예약을 한꺼번에 잡고(기본값·미리 보기·등록), 묶음의 `이후 전부`를 옮기고·고치고·취소하며, 보호자에게 보낼 글과 알림톡 줄이 한 통으로 정리되게 한다.

**Architecture:** `visit` 스포크에 묶음 표 `visit_series` 와 `visits.series_id` 를 더한다. 회차·이후 전부·걸린 회차·자리 계산은 순수 함수(`domain/services/visit_series.py`)이고, 이후 전부의 잠금은 `app/services/series_scope.py` 한 곳이 한다. 알림은 이벤트 칸 셋(`series_followup`·`quiet`)으로 `notification` 이 가른다.

**Tech Stack:** Python 3.13 · FastAPI · SQLAlchemy 2.0 asyncio · Alembic · pytest (`infra/` 에서 docker compose)

**Spec:** `docs/superpowers/specs/2026-11-16-pass-recurring-design.md` (3.7·4절·5.1~5.4·5.6 ⑭-1·6절 P12~P16·7절), 공통 기준 `docs/superpowers/specs/2026-11-16-next-designs-common.md` (4·8·10·11절)

## Global Constraints

- 문서·주석·테스트 이름·커밋 메시지는 한국어. 커밋 끝에 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. 저장소 루트에서 `git add -A` 하지 않는다(경로를 적는다).
- 간격 1~12주, 횟수 2~12회(첫 예약 포함), 횟수 기본값 6, 간격 기본값 = ⑬ 의 아이 주기를 1~12 로 자른 값(여러 마리면 짧은 쪽) → 매장의 기본 간격(`default_cycle_weeks`, 1~12 로 자름).
- 회차는 같은 요일·같은 벽시계 시각(`visit_cycle.next_start` 와 같은 계산). 예약 가능 범위(오늘 기준 1년, `check_start`)를 넘는 회차는 목록에서 빠진다.
- 휴무·겹침은 **경고만** 한다. 반복은 `walk_in` 에 싣지 못한다.
- `이후 전부` = 같은 묶음 · 시작 시각이 이 예약 이상 · `reserved`(가족 `family=false` 면 요청한 방문의 아이만). 미용 중·완료·취소·노쇼·앞선 것은 건드리지 않는다. 걸린 회차가 하나라도 있으면 **아무것도 바꾸지 않고** 409 `VISIT_SERIES_CONFLICT`.
- 새 이벤트 칸은 기본값을 갖고 `family_pet_ids` **앞에** 둔다: `VisitReserved.series_followup: bool = False`, `VisitRescheduled.quiet: bool = False`, `VisitCanceled.quiet: bool = False`.
- 검색되는 글에 닿는 쓰기는 **방문마다** `SearchSourceChanged(ctx, "visit", visit_id)` 를 낸다(등록·이후 전부 옮기기·고치기).
- 잠금 순서: 고객 행(`CustomerDirectoryPort.lock_family`) → 방문 행(ID 오름차순, 한 번의 `lock`). 잠근 뒤 다시 읽은 값으로 대상을 고른다. 잠금을 쥔 채 외부 HTTP 를 부르지 않는다.
- 새 권한을 만들지 않는다: 쓰기는 `require_permission("reservation:write")`, 읽기는 `get_shop_context`. 로그인 없는 경로는 늘지 않는다.
- 보호자에게 보낼 글(묶음 토막·알림 글)과 아이 이름을 로그·오류 메시지·예외 문자열에 싣지 않는다. 오류의 `details` 에는 방문 ID·아이 ID·시각·사유 코드만 싣는다.
- 마이그레이션은 `0026`, 결정 기록은 `_docs/decisions/017-pass-recurring.md`(⑭ 전체가 함께 쓴다 — 이 묶음은 반복 예약 절).
- 명령은 모두 `infra/` 에서: 단위 `docker compose run --rm --no-deps backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"`, 통합 `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration`, 계약 `docker compose run --rm --no-deps backend lint-imports --config .importlinter`, 라우트 표 `docker compose run --rm --no-deps auth python scripts/print_routes.py`. 긴 출력은 스크래치 파일로 보내고 꼬리만 읽는다.

## Review Focus

1. **주마다 묶음을 `이후 전부` 로 1주 미는 경우** — 회차마다 바로 다음 회차의 옛 자리로 간다. 같은 아이·같은 시각의 부분 유일 색인이 한 문장 UPDATE 중간에 거짓 충돌을 내면 안 된다 → Task 2 의 저장소 테스트(`move_each` 를 늦은 것부터)와 Task 8 의 통합 테스트가 고정한다.
2. **마지막 회차가 1년 범위를 넘게 밀리는 경우** — 422 로 막다른 길이 아니라 그 회차가 `out_of_range` 걸린 회차로 나와 [그 회차만 빼고]로 진행할 수 있어야 한다 → Task 1 `conflicts_of`, Task 6 인터랙터 테스트.
3. **묶음 안에 미용 중·완료·`이 예약만` 취소가 섞인 가족** — `이후 전부` 는 뒤의 예약됨만, 자리(`6번 중 3번째`)와 마지막 판정은 취소를 빼고 센다 → Task 5 `series_position`, Task 7 인터랙터 테스트.
4. **첫 회차를 빼고 등록** — 처음 만든 방문(2회차)이 접수 안내를 받고(`series_followup=False`) 나머지는 리마인드만 → Task 4 인터랙터 테스트.
5. **새 칸을 모르는 예전 앱** — `repeat`·`scope`·`family`·`skip_visit_ids` 가 없는 요청과 묶음이 없는 방문의 `scope=following` 은 지금과 똑같이 동작한다 → Task 4·6·7 의 "예전 요청" 테스트.

## Rulings (계획 때 정한 것 — 설계와 다른 곳)

- **반복 등록의 응답에는 보낼 글 토막을 싣지 않는다.** 앱은 지금처럼 첫 방문으로 `POST /visits/{id}/send-bundle` 을 부르고, 묶음 조립이 그 예약부터의 회차를 전부 적는다 — 동의서 링크도 그 길에서만 만들어진다(길 하나). `이후 전부` 옮기기·고치기(시각이 바뀐 때)·취소의 응답에는 `notice`(토막 목록)를 싣는다.
- 간격 기본값의 근거는 `cycle`·`shop` 둘이다 — 매장의 기본 간격은 늘 있다(행이 없어도 4). `fallback` 은 두지 않는다.
- `repeat-defaults` 의 `customer_id` 는 받기만 한다 — ⑭-4 가 남은 횟수권으로 횟수 기본값을 바꿀 때 쓴다.
- 묶음이 없는 방문에 `scope=following` 이 오면 `this` 로 한다(오류가 아니다). `family`·`skip_visit_ids` 는 `following` 일 때만 뜻이 있다.
- 걸린 회차는 두 가지다 — `taken`(그 아이에게 그 시각 살아 있는 예약이 이미 있다)과 `out_of_range`(1년 범위 밖). 둘 다 409 `VISIT_SERIES_CONFLICT` 의 `details.conflicts` 로 간다. 오류 응답에 `details` 를 싣는 길은 `core/http_errors.py` 에 하나 더한다(예외에 `details` 속성이 있을 때만).
- `이후 전부` 고치기에서 반려동물을 바꾸면 422 — 아이 바꾸기는 `이 예약만` 이다.
- 묶음의 예약 목록은 따로 읽는다 — `GET /visit-series/{series_id}`(없으면 404 `VISIT_SERIES_NOT_FOUND`). 방문 상세에는 `series` 요약 한 칸.
- 자리 계산(`position`·`total`·`is_last`)은 묶음 방문 가운데 **취소를 뺀** 시작 시각들(가족은 한 번)로 센다. 그 방문 자신이 취소됐으면 자신은 넣는다.
- 다음 예약 초안에 `upcoming_starts_at`(그 아이들의 이 방문 뒤 가장 이른 살아 있는 예약)과 `repeat`(이 방문이 묶음의 마지막이면 같은 간격·횟수 6·다음 시각)를 더한다 — ⑭-2 의 완료 시트가 쓴다.
- 미리 보기의 경고는 회차마다 지금의 `warnings_after_save` 를 부른다(회차 12 개면 작은 질의 24 번) — 1년 범위를 한 번에 읽지 않는다.
- 미리 보기는 GET(목록은 `pet_ids=&pet_ids=` 처럼 반복) — `GET /visit-checks` 와 같은 모양.

---

### Task 1: 회차·이후 전부·걸린 회차·자리 계산과 보낼 글 토막 (순수 함수)

**Files:**
- Create: `backend/apps/visit/domain/services/visit_series.py`
- Modify: `backend/apps/visit/domain/services/send_bundle.py`
- Modify: `backend/apps/visit/domain/entities/visit.py` (칸 `series_id: int | None = None` — `report_skipped_at` 뒤, `has_live_report` 앞)
- Test: `backend/apps/visit/tests/domain/test_visit_series.py`, `backend/apps/visit/tests/domain/test_send_bundle.py`

**Interfaces:**
- Produces (`visit_series.py`):
  - 상수 `MIN_INTERVAL_WEEKS = 1`, `MAX_INTERVAL_WEEKS = 12`, `MIN_COUNT = 2`, `MAX_COUNT = 12`, `DEFAULT_COUNT = 6`, `TAKEN = "taken"`, `OUT_OF_RANGE = "out_of_range"`, `CYCLE = "cycle"`, `SHOP = "shop"`.
  - `@dataclass(frozen=True) Occurrence(index: int, starts_at: datetime)` — index 는 1 부터, starts_at 은 UTC.
  - `plan_occurrences(first: datetime, interval_weeks: int, count: int, tz: str, now: datetime) -> tuple[list[Occurrence], int]` — 범위 안의 회차와 범위 밖으로 빠진 수.
  - `within_horizon(starts_at: datetime, now: datetime, tz: str) -> bool` — `check_start` 의 범위 규칙과 같은 판정(매장 시간대 날짜 차이 ≤ `BOOKING_HORIZON_DAYS`, 뒤쪽도 같다).
  - `clip_interval(weeks: int) -> int` — 1~12.
  - `@dataclass(frozen=True) RepeatInterval(weeks: int, source: str, pet_id: int | None, cycle_weeks: int | None)`.
  - `repeat_interval(cycles: dict[int, PetCycle], shop_default_weeks: int) -> RepeatInterval` — `(weeks, pet_id)` 가 가장 작은 아이를 고른다(⑬ `shortest` 와 같은 짧은 쪽). 그 아이의 출처가 `manual`·`computed` 면 `CYCLE`(pet_id·자르기 전 cycle_weeks), 아니면 `SHOP`(pet_id·cycle_weeks 는 None, weeks 는 매장 값을 자른 것). 아이가 없으면 `SHOP`.
  - `wall_delta(before: datetime, after: datetime, tz: str) -> timedelta`, `wall_shift(starts_at: datetime, delta: timedelta, tz: str) -> datetime` — 매장 시간대 벽시계 차이를 그대로 민다(UTC 로 돌려준다).
  - `following_of(series: Sequence[Visit], anchors: Sequence[Visit], *, family: bool, skip_ids: frozenset[int] = frozenset()) -> list[Visit]` — anchors 는 같은 `starts_at`. `reserved` · `starts_at >= anchors[0].starts_at` · (`family` 이거나 `pet_id` 가 anchors 의 아이들 가운데 하나 — None 포함) · `skip_ids` 밖. (starts_at, id) 순.
  - `earliest_ids(visits: Sequence[Visit]) -> frozenset[int]` — 시작 시각이 가장 이른 방문들의 ID(가장 가까운 회차 — 알림을 내는 쪽).
  - `move_order(moves: Sequence[tuple[Visit, datetime]]) -> list[tuple[Visit, datetime]]` — 늦게 미는 묶음이면 지금 시각이 늦은 것부터, 당기는 묶음이면 이른 것부터(같으면 ID 순). 같은 아이가 다음 회차의 옛 자리로 갈 때 유일 색인에 걸리지 않게 하는 차례다.
  - `@dataclass(frozen=True) SeriesConflict(visit_id: int, pet_id: int | None, starts_at: datetime, reason: str)`.
  - `conflicts_of(moves: Sequence[tuple[Visit, datetime]], occupied: Sequence[Visit], now: datetime, tz: str) -> list[SeriesConflict]` — occupied 는 그 보호자의 새 시각들에 있는 살아 있는 방문(옮기는 방문 자신은 부르는 쪽이 뺀다). 같은 아이(아이가 없으면 같은 보호자의 아이 없는 방문)·같은 새 시각이면 `TAKEN`, 범위 밖이면 `OUT_OF_RANGE`(둘 다면 `OUT_OF_RANGE`). 옮기는 차례(starts_at, id)대로.
  - `@dataclass(frozen=True) SeriesPosition(position: int, total: int, is_last: bool)`.
  - `series_position(series: Sequence[Visit], visit: Visit) -> SeriesPosition` — 취소가 아닌 방문(과 그 방문 자신)의 서로 다른 시작 시각을 늘어놓고 그 방문의 자리.
- Produces (`send_bundle.py`):
  - 상수 `SERIES_CHANGE = "series_change"`, `SERIES_CANCEL = "series_cancel"`.
  - `series_lines(starts: Sequence[datetime], interval_weeks: int) -> str` — 매장 시간대 시각들(서로 다른 것만, 오름차순)을 `"{N}주마다 {M}번 예약했어요\n· 11월 20일(금) 오후 2:00\n· …"` 로.
  - `build_bundle(…, series_starts: Sequence[datetime] = (), interval_weeks: int | None = None)` — `series_starts` 가 둘 이상이면 예약 토막 글 끝에 빈 줄 하나와 `series_lines(...)` 를 붙인다(토막은 그대로 하나).
  - `series_notice(kind: str, *, shop_name: str, pet_names: Sequence[str], starts: Sequence[datetime]) -> BundlePart` — `series_change`: `"[{매장}] 예약 날짜를 바꿨어요.\n{아이}\n· …"`, `series_cancel`: `"[{매장}] 예약을 취소했어요.\n{아이}\n· …"`. 아이 이름이 없으면 그 줄이 없다. 이름은 `" · "` 로 잇는다. 시각 줄은 `· {day_label} {time_label}`.

- [ ] **Step 1: 실패하는 테스트를 쓴다** — `test_visit_series.py` (시각은 `builders.kst`, tz `"Asia/Seoul"`, NOW = `kst(11, 17, 10)`):

```python
def test_회차는_같은_요일_같은_시각이고_1년을_넘는_회차는_빠진다():
    kept, beyond = plan_occurrences(kst(11, 20, 14), 4, 6, SEOUL, NOW)
    assert [o.index for o in kept] == [1, 2, 3, 4, 5, 6]
    assert kept[1].starts_at == kst(12, 18, 14) and beyond == 0
    kept, beyond = plan_occurrences(kst(11, 20, 14), 12, 6, SEOUL, NOW)   # 12주 × 5 = 60주 뒤는 범위 밖
    assert [o.index for o in kept] == [1, 2, 3, 4, 5] and beyond == 1

def test_간격_기본값은_아는_주기의_짧은_쪽을_1에서_12로_자르고_모르면_매장_값():
    cycles = {101: cycle(weeks=16, source="computed"), 102: cycle(weeks=20, source="manual")}
    assert repeat_interval(cycles, 4) == RepeatInterval(12, CYCLE, 101, 16)
    assert repeat_interval({101: cycle(weeks=4, source="none")}, 30) == RepeatInterval(4, SHOP, None, None)
    assert repeat_interval({}, 30) == RepeatInterval(12, SHOP, None, None)

def test_이후_전부는_같은_시각_이상의_예약됨만이고_가족을_고를_수_있다(): ...
    # 가족 101·102 의 묶음 1~4회차, 2회차 102 는 완료, 3회차 101 은 미용 중, 1회차는 앞선 것
    # anchors = 2회차 101 → family=True: [2회차 101, 3회차 102, 4회차 101, 4회차 102]
    # family=False: [2회차 101, 4회차 101] / skip_ids={4회차 101 의 id} 이면 빠진다

def test_늦게_미는_묶음은_늦은_회차부터_당기는_묶음은_이른_회차부터_옮긴다(): ...

def test_걸린_회차는_같은_아이의_살아_있는_예약과_1년_범위_밖이다():
    # 2회차 → 3회차 자리로 가는데 3회차는 옮기는 대상이라 occupied 에 없다 → 걸리지 않음
    # 다른 예약(묶음 밖)이 새 시각에 있으면 TAKEN, 형제 아이의 예약이면 걸리지 않음
    # 새 시각이 NOW + 366일이면 OUT_OF_RANGE

def test_자리는_취소를_빼고_가족은_한_번_세며_취소된_방문은_자기를_넣는다():
    # 6회차 중 5회차 취소 → 4회차는 SeriesPosition(4, 5, False), 6회차는 (5, 5, True)
    # 취소된 5회차 자신은 (5, 6, False)
```

  `test_send_bundle.py` 에 더한다:

```python
def test_반복_묶음이면_예약_토막_끝에_회차를_전부_적는다():
    parts = build_bundle(..., starts_at=local(11, 20, 14), series_starts=[local(11, 20, 14), local(12, 18, 14)], interval_weeks=4)
    assert [p.kind for p in parts] == ["reservation"]
    assert parts[0].text.endswith("\n\n4주마다 2번 예약했어요\n· 11월 20일(금) 오후 2:00\n· 12월 18일(금) 오후 2:00")

def test_회차가_하나면_목록을_붙이지_않는다(): ...

def test_이후_전부의_안내_글은_바뀐_회차를_전부_적는다():
    part = series_notice(SERIES_CANCEL, shop_name="Hiss Haus", pet_names=["콩이", "두부"], starts=[...두 시각...])
    assert part == BundlePart("series_cancel", "[Hiss Haus] 예약을 취소했어요.\n콩이 · 두부\n· 12월 18일(금) 오후 2:00\n· 1월 15일(목) 오후 2:00")
    assert "\n\n" not in series_notice(SERIES_CHANGE, shop_name="Hiss Haus", pet_names=[], starts=[...]).text
```

- [ ] **Step 2: 실패를 확인한다** — `docker compose run --rm --no-deps backend pytest apps/visit/tests/domain/test_visit_series.py apps/visit/tests/domain/test_send_bundle.py -q -p no:cacheprovider` → `ModuleNotFoundError: visit.domain.services.visit_series` 와 `series_lines`·`series_notice` import 실패.
- [ ] **Step 3: 구현한다** — 위 Interfaces 그대로. `plan_occurrences` 는 `next_start(first, interval*(i-1), tz)` 로 회차를 내고 `within_horizon` 으로 거른다. `Visit.series_id` 칸을 더한다(기본 None — 빌더·매퍼는 Task 2).
- [ ] **Step 4: 통과를 확인한다** — 같은 명령 → 전부 통과, 그리고 visit 단위 전체 `docker compose run --rm --no-deps backend pytest apps/visit -q -p no:cacheprovider -m "not integration and not network"` → 통과.
- [ ] **Step 5: 커밋** — `git add backend/apps/visit/domain/services/visit_series.py backend/apps/visit/domain/services/send_bundle.py backend/apps/visit/domain/entities/visit.py backend/apps/visit/tests/domain/test_visit_series.py backend/apps/visit/tests/domain/test_send_bundle.py && git commit -m "feat(backend): ⑭ 반복 회차·이후 전부·걸린 회차·자리 계산과 보낼 글 토막(순수 함수)"`

### Task 2: 묶음 표·칸과 저장소, 오류의 details

**Files:**
- Create: `backend/alembic/versions/0026_visit_series.py`, `backend/apps/visit/domain/entities/visit_series.py`, `backend/apps/visit/app/ports/output/visit_series_repository.py`, `backend/apps/visit/adapter/outbound/pg/visit_series_pg_repository.py`
- Modify: `backend/apps/visit/adapter/outbound/orm/visit_orm.py` (`VisitSeriesOrm`, `VisitOrm.series_id`), `backend/apps/visit/adapter/outbound/mappers/visit_mapper.py`, `backend/apps/visit/domain/value_objects/new_visit.py` (`series_id: int | None = None`), `backend/apps/visit/app/ports/output/visit_lookup_repository.py`, `backend/apps/visit/app/ports/output/visit_write_repository.py`, `backend/apps/visit/adapter/outbound/pg/visit_pg_repository.py`, `backend/apps/visit/dependencies/visit_wiring.py` (`build_visit_series_repository(db)`), `backend/apps/visit/domain/errors.py`, `backend/apps/visit/adapter/inbound/api/error_map.py`, `backend/core/http_errors.py`, `backend/apps/visit/tests/helpers/fakes.py` (`FakeVisits` 새 메서드, `FakeSeries`), `backend/apps/visit/tests/helpers/builders.py`(필요하면)
- Test: `backend/apps/visit/tests/adapter/test_visit_pg_repository.py`, `backend/apps/visit/tests/adapter/test_visit_series_pg_repository.py`, `backend/tests/test_http_errors.py`, `backend/apps/visit/tests/adapter/test_report_error_map.py`(코드 표가 있으면 그 자리)

**Interfaces:**
- Consumes: Task 1 의 `SeriesConflict`, `Visit.series_id`.
- Produces:
  - 표 `visit_series(id bigint PK, shop_id bigint NOT NULL, customer_id bigint NOT NULL, interval_weeks smallint NOT NULL CHECK (interval_weeks BETWEEN 1 AND 12) — 이름 ck_visit_series_interval_weeks, created_by_member_id bigint NOT NULL, created_at timestamptz NOT NULL DEFAULT now())`, 색인 `ix_visit_series_shop_customer(shop_id, customer_id)`. `visits.series_id bigint NULL` + 외래 키 `fk_visits_series_id → visit_series.id`(같은 스포크) + 부분 색인 `ix_visits_series(series_id) WHERE series_id IS NOT NULL`. downgrade 는 셋을 지운다(실행은 사용자 확인 없이 하지 않는다).
  - `VisitSeries(id: int, shop_id: int, customer_id: int, interval_weeks: int, created_by_member_id: int, created_at: datetime)` (frozen dataclass).
  - `VisitSeriesRepository`: `create(ctx, customer_id: int, interval_weeks: int, member_id: int) -> VisitSeries`, `get(ctx, series_id: int) -> VisitSeries`(이 매장의 것이 아니면 `VisitSeriesNotFoundError`).
  - `VisitLookupRepository.list_series(ctx, series_id: int) -> list[Visit]`(상태 무관, (starts_at, id) 순), `VisitLookupRepository.active_at(ctx, customer_id: int, starts: Sequence[datetime]) -> list[Visit]`(그 보호자의 살아 있는 방문 가운데 시작 시각이 starts 에 든 것).
  - `VisitWriteRepository.move_each(ctx, moves: Sequence[tuple[int, datetime]]) -> list[Visit]` — **주어진 차례대로** 한 줄씩 `starts_at` 을 바꾼다(유일 위반은 `VisitDuplicateError`, 세이브포인트 하나). 돌려주는 것은 다시 읽은 방문(ID 순).
  - `create_many` 가 `NewVisit.series_id` 를 쓴다.
  - 오류: `VisitSeriesNotFoundError`(code `VISIT_SERIES_NOT_FOUND`, 404), `VisitSeriesConflictError(conflicts: Sequence[SeriesConflict], tz: str)`(code `VISIT_SERIES_CONFLICT`, 409, 메시지 `"이미 예약이 있거나 잡을 수 없는 회차가 있어요."`, 속성 `details = {"conflicts": [{"visit_id", "pet_id", "starts_at"(매장 시간대 ISO), "reason"}]}`).
  - `core/http_errors.py` 의 도메인 오류 처리기: 예외에 `details` 속성이 있고 None 이 아니면 본문에 `"details"` 를 더한다. 없으면 지금 본문 그대로.

- [ ] **Step 1: 실패하는 테스트를 쓴다**
  - `test_visit_pg_repository.py`: `test_주마다_묶음을_1주_늦게_옮겨도_늦은_회차부터면_유일_색인에_걸리지_않는다` — 같은 아이의 예약 셋(11/20·11/27·12/4 14:00, 같은 series)을 `move_each([(c, 12/11), (b, 12/4), (a, 11/27)])` → 세 방문이 한 주씩 밀려 있다. `test_move_each_가_묶음_밖_예약과_겹치면_VISIT_DUPLICATE` . `test_list_series_는_상태와_상관없이_시작_시각_순이고_다른_매장의_것은_없다`. `test_active_at_은_그_보호자의_살아_있는_방문만`. `test_create_many_가_series_id_를_적는다`.
  - `test_visit_series_pg_repository.py`: `test_묶음을_만들고_읽는다`, `test_다른_매장의_묶음은_VISIT_SERIES_NOT_FOUND`.
  - `tests/test_http_errors.py`: `test_도메인_오류에_details_가_있으면_본문에_싣는다`(`{"code","message","details"}`), `test_details_가_없으면_본문은_두_칸이다`.
- [ ] **Step 2: 실패를 확인한다** — `docker compose run --rm backend pytest apps/visit/tests/adapter/test_visit_pg_repository.py apps/visit/tests/adapter/test_visit_series_pg_repository.py tests/test_http_errors.py -q -p no:cacheprovider` → import·속성 오류로 실패.
- [ ] **Step 3: 구현한다** — 마이그레이션·ORM·매퍼·포트·pg·가짜(`FakeVisits.list_series`·`active_at`·`move_each` — `move_each` 는 한 줄씩 `_clash` 를 보고 옮긴다, `FakeSeries` 는 `create`·`get` 과 `journal` 기록)·오류·처리기. `test_fakes_are_ports` 가 통과해야 한다.
- [ ] **Step 4: 통과를 확인한다** — 같은 명령, 그리고 `docker compose run --rm backend pytest tests/test_schema_drift.py -q -p no:cacheprovider` → 통과(ORM 과 마이그레이션이 같다). visit 단위 전체 통과.
- [ ] **Step 5: 커밋** — 위 Files 를 적어 `git commit -m "feat(backend): ⑭ 반복 묶음 표(0026)·visits.series_id·저장소와 오류 응답의 details"`

### Task 3: 반복 기본값과 미리 보기 (읽기 둘)

**Files:**
- Create: `backend/apps/visit/app/ports/input/get_repeat_defaults_use_case.py`, `backend/apps/visit/app/dtos/get_repeat_defaults_dto.py`, `backend/apps/visit/app/use_cases/get_repeat_defaults_interactor.py`, `backend/apps/visit/adapter/inbound/api/schemas/get_repeat_defaults_schema.py`, `backend/apps/visit/adapter/inbound/api/v1/get_repeat_defaults_router.py`, `backend/apps/visit/dependencies/get_repeat_defaults_provider.py`, 같은 다섯을 `preview_repeat` 이름으로, `backend/apps/visit/app/services/booking_inputs.py`
- Modify: `backend/main.py` (두 라우터를 `get_visit_router` **앞**에 include — `/visits/{visit_id}` 가 먼저 잡지 않게), `backend/apps/visit/app/use_cases/register_visit_interactor.py`(메뉴·소요 계산을 `booking_inputs` 로 옮긴다 — 동작은 그대로)
- Test: `backend/apps/visit/tests/app/use_cases/test_get_repeat_defaults_interactor.py`, `test_preview_repeat_interactor.py`, `backend/apps/visit/tests/adapter/test_get_repeat_defaults_router.py`, `test_preview_repeat_router.py`

**Interfaces:**
- Consumes: Task 1 `plan_occurrences`·`repeat_interval`·`DEFAULT_COUNT`, Task 2 `active_at`, ⑬ `app/services/revisit.pet_cycles`, `visit_warnings.warnings_after_save`.
- Produces:
  - `booking_inputs.chosen_duration(ctx, menu_ids: Sequence[int], duration_minutes: int | None, menus: MenuRepository, settings: ScheduleSettings) -> int` — 고를 수 없는 메뉴면 `MenuNotAvailableError`, 소요가 없으면 `default_duration`, 그다음 `check_duration`.
  - `GET /v1/shops/{shop_id}/visits/repeat-defaults?customer_id=&pet_ids=` (get_shop_context) → `{interval_weeks, source: "cycle"|"shop", pet_id: int|null, cycle_weeks: int|null, count}`. 쿼리 `GetRepeatDefaultsQuery(ctx, customer_id: int, pet_ids: tuple[int, ...])`, 뷰 `RepeatDefaultsView(interval_weeks, source, pet_id, cycle_weeks, count)`. 인터랙터 `GetRepeatDefaultsInteractor(history: VisitHistoryRepository, *, directory: CustomerDirectoryPort, settings: RevisitSettingsRepository, now)`.
  - `GET /v1/shops/{shop_id}/visits/repeat-preview?customer_id=&pet_ids=&starts_at=&duration_minutes=&menu_ids=&interval_weeks=&count=` (get_shop_context) → `{interval_weeks, count, occurrences: [{index, starts_at, warnings: [str], taken: bool}], beyond_horizon}`. 쿼리 `PreviewRepeatQuery(ctx, customer_id, pet_ids, starts_at, duration_minutes: int | None, menu_ids: tuple[int, ...], interval_weeks, count)`, 뷰 `RepeatPreviewView`·`OccurrenceView(index, starts_at(매장 시간대), warnings, taken)`. 인터랙터 `PreviewRepeatInteractor(visits: VisitLookupRepository, board: VisitBoardRepository, menus: MenuRepository, schedule: ScheduleRepository, now)`.
  - 쿼리 검증(스키마, 어기면 422 `VALIDATION_ERROR`): `customer_id`·ID 는 `EntityId`, `pet_ids`·`menu_ids` 10 개까지·중복 없음, `interval_weeks` 1~12, `count` 2~12, `starts_at` 은 시간대가 붙은 시각.
  - `taken` = 그 회차 시각에 `pet_ids` 의 아이(아이가 없으면 보호자의 아이 없는 방문)의 살아 있는 예약이 있다. 한 번의 `active_at` 으로 읽는다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**
  - 기본값: `test_아이의_계산한_주기를_간격으로_쓰고_근거와_아이를_준다`(완료 다섯 번, 35일 간격 → `RepeatDefaultsView(5, "cycle", 101, 5, 6)`), `test_주기를_모르면_매장의_기본_간격`(`revisit_settings` 기본 간격 30 → interval 12, source shop), `test_여러_마리면_짧은_쪽`, `test_아이가_없으면_매장_값`.
  - 미리 보기: `test_회차마다_시각과_경고를_준다`(둘째 회차 날짜를 휴무일로 → 그 회차만 `["closed_day"]`), `test_1년을_넘는_회차는_없고_그_수를_준다`, `test_그_아이가_이미_그_시각에_예약이_있으면_taken`(형제 아이의 예약이면 taken 이 아니다), `test_고를_수_없는_메뉴면_MENU_NOT_AVAILABLE`, `test_첫_시각이_범위_밖이면_VISIT_INPUT`, `test_자정을_넘기면_VISIT_CROSSES_MIDNIGHT`.
  - 라우터: `test_repeat_defaults_는_멤버가_읽고_칸을_고정한다`, `test_repeat_preview_의_간격_13_횟수_1_은_422`, `test_repeat_preview_는_pet_ids_를_반복_쿼리로_받는다`.
- [ ] **Step 2: 실패를 확인한다** — `docker compose run --rm --no-deps backend pytest apps/visit/tests -q -p no:cacheprovider -k "repeat_defaults or preview_repeat"` → import 실패.
- [ ] **Step 3: 구현한다** — 위 Interfaces. 미리 보기 순서: 범위 검사(`check_start(starts_at)`) → `ensure` → `chosen_duration` → `check_same_day` → `plan_occurrences` → `active_at` 한 번 → 회차마다 `warnings_after_save`. 등록은 `chosen_duration` 을 부르도록만 바꾼다(지금 테스트가 그대로 통과).
- [ ] **Step 4: 통과를 확인한다** — 같은 명령 → 통과. visit 단위 전체·`lint-imports` 통과.
- [ ] **Step 5: 커밋** — `git commit -m "feat(backend): ⑭ 반복 간격·횟수의 기본값과 회차 미리 보기"`

### Task 4: 반복 등록과 접수 안내 한 통

**Files:**
- Modify: `backend/apps/visit/app/dtos/register_visit_dto.py` (`RepeatRequest`, `RegisterVisitCommand.repeat`, `RegisteredVisitsView.series`), `backend/apps/visit/app/use_cases/register_visit_interactor.py`, `backend/apps/visit/adapter/inbound/api/schemas/register_visit_schema.py`, `backend/apps/visit/adapter/inbound/api/v1/register_visit_router.py`(명령에 옮겨 담기), `backend/apps/visit/dependencies/register_visit_provider.py`, `backend/apps/hub/app/dtos/visit_events.py` (`VisitReserved.series_followup`), `backend/apps/notification/app/use_cases/handle_visit_event_interactor.py`
- Test: `backend/apps/visit/tests/app/use_cases/test_register_visit_interactor.py`, `backend/apps/visit/tests/adapter/test_register_visit_router.py`, `backend/apps/notification/tests/app/use_cases/test_handle_visit_event_interactor.py`

**Interfaces:**
- Consumes: Task 1 `plan_occurrences`, Task 2 `VisitSeriesRepository.create`·`NewVisit.series_id`, Task 3 `chosen_duration`.
- Produces:
  - `RepeatRequest(interval_weeks: int, count: int, skip: tuple[int, ...] = ())` — skip 은 회차 번호(1 부터).
  - 요청 칸 `repeat: {interval_weeks 1~12, count 2~12, skip: [1~count, 중복 없음, 11 개까지]} | null = null`(skip 이 count 를 넘으면 422).
  - 응답 칸 `series: {id, interval_weeks, occurrences: [{starts_at, warnings}]} | null` — 뷰 `RegisteredSeriesView(id, interval_weeks, occurrences: list[SeriesOccurrenceView(starts_at, warnings)])`. `warnings` 칸은 지금처럼 첫 회차의 경고다.
  - `RegisterVisitInteractor(..., series: VisitSeriesRepository)`(키워드).
  - `VisitReserved.series_followup: bool = False` — `revived` 다음, `family_pet_ids` 앞.
  - notification `_reserved`: `series_followup` 이면 접수 안내(`confirm`)를 만들지 않는다(리마인드는 지금처럼).
- 규칙: `repeat` 과 `walk_in` 을 함께 보내면 `VisitInputError`. 빼고 남은 회차가 둘보다 적으면 `VisitInputError("반복 예약은 두 번 이상이어야 해요.")`. 범위 밖 회차는 조용히 빠진다(미리 보기와 같다). 고객 행 잠금 → 묶음 만들기 → `create_many` 한 번(회차 × 아이). 가장 이른 회차의 방문은 `series_followup=False`, 나머지는 `True`. `family_pet_ids` 는 회차마다 그 회차의 아이들. `SearchSourceChanged` 는 방문마다. 회차의 경고는 회차마다 `warnings_after_save`.

- [ ] **Step 1: 실패하는 테스트를 쓴다**
  - `test_반복이면_회차마다_가족_방문을_만들고_같은_묶음에_넣는다` — 101·102, 4주·3회 → 방문 여섯, `series_id` 하나, 회차 시각 11/20·12/18·1/15 14:00, journal 에서 `lock_family` < `create_series` < `create_visits`.
  - `test_첫_회차만_접수_안내이고_나머지는_리마인드만` — 이벤트 여섯의 `series_followup` 이 `[False, False, True, True, True, True]`, `family_pet_ids` 가 모두 `(101, 102)`.
  - `test_첫_회차를_빼면_둘째_회차가_접수_안내를_받는다`(Review Focus 4).
  - `test_빼고_남은_회차가_하나면_VISIT_INPUT`, `test_지금_시작에는_반복을_싣지_못한다`, `test_1년을_넘는_회차는_조용히_빠진다`.
  - `test_방문마다_검색_이벤트를_낸다`(SearchSourceChanged 여섯).
  - `test_회차가_이미_예약된_시각이면_전부_VISIT_DUPLICATE`(아무것도 만들지 않는다 — 가짜의 rows 그대로).
  - `test_repeat_없는_예전_요청은_묶음_없이_지금처럼`(Review Focus 5 — `series` 칸 None, 방문의 `series_id` None, 이벤트 칸 기본값).
  - 라우터: `test_repeat_칸을_명령으로_옮긴다`, `test_count_1_interval_13_skip_범위_밖은_422`, `test_응답에_series_가_있다`.
  - notification: `test_반복의_둘째_회차부터는_접수_안내_없이_리마인드만`(`_event(VisitReserved, series_followup=True)` → `confirm` 줄 없음, `reminder` 줄 하나).
- [ ] **Step 2: 실패를 확인한다** — `docker compose run --rm --no-deps backend pytest apps/visit/tests/app/use_cases/test_register_visit_interactor.py apps/visit/tests/adapter/test_register_visit_router.py apps/notification/tests/app/use_cases/test_handle_visit_event_interactor.py -q -p no:cacheprovider` → 실패.
- [ ] **Step 3: 구현한다** — 위 규칙대로.
- [ ] **Step 4: 통과를 확인한다** — 같은 명령, 그리고 단위 전체(`apps tests`) → 통과.
- [ ] **Step 5: 커밋** — `git commit -m "feat(backend): ⑭ 반복 등록 — 회차마다 같은 묶음, 접수 안내는 첫 회차 한 통(series_followup)"`

### Task 5: 묶음을 읽는 곳 — 방문 상세·묶음 목록·다음 예약 초안·보낼 것 묶음

**Files:**
- Create: `get_visit_series` 의 use_case·dto·interactor·schema·router·provider 여섯(경로 `GET /v1/shops/{shop_id}/visit-series/{series_id}`, get_shop_context), `backend/apps/visit/adapter/inbound/api/path_params.py` 에 `SeriesId`
- Modify: `backend/apps/visit/app/dtos/get_visit_dto.py`(`SeriesBriefView`, `VisitDetailView.series: SeriesBriefView | None = None`), `get_visit_interactor.py`·스키마·프로바이더, `get_next_visit_draft_dto.py`(`upcoming_starts_at: datetime | None = None`, `repeat: RepeatDraftView | None = None`)·인터랙터·스키마·프로바이더, `backend/apps/visit/app/ports/output/visit_history_repository.py`(`next_active_after`)·pg·가짜, `build_send_bundle_interactor.py`·프로바이더, `backend/main.py`
- Test: `test_get_visit_interactor.py`, `test_get_visit_series_interactor.py`, `test_get_next_visit_draft_interactor.py`, `test_build_send_bundle_interactor.py`(없으면 만든다), 라우터 테스트 `test_get_visit_series_router.py`·`test_get_visit_router.py`·`test_get_next_visit_draft_router.py`, `test_visit_pg_repository.py`(`next_active_after`)

**Interfaces:**
- Consumes: Task 1 `series_position`·`DEFAULT_COUNT`·`series_lines` 의 `build_bundle(series_starts, interval_weeks)`, Task 2 `list_series`·`VisitSeriesRepository.get`, ⑬ `next_start`.
- Produces:
  - 상세 `series: {id, interval_weeks, position, total, is_last} | null` — `SeriesBriefView(id, interval_weeks, position, total, is_last)`.
  - `GET /visit-series/{series_id}` → `{id, interval_weeks, visits: [VisitSchema]}`(상태 무관, 시작 시각·ID 순) — `GetVisitSeriesInteractor(visits: VisitLookupRepository, series: VisitSeriesRepository, directory, menus)`, 없으면 404 `VISIT_SERIES_NOT_FOUND`.
  - `VisitHistoryRepository.next_active_after(ctx, customer_id: int, pet_ids: Sequence[int], after: datetime) -> datetime | None` — 그 아이들(빈 목록이면 보호자의 아이 없는 방문)의 살아 있는 방문 가운데 `starts_at > after` 인 가장 이른 시각.
  - 초안 `upcoming_starts_at`(매장 시간대) · `repeat: {interval_weeks, count, starts_at} | null` — 이 방문의 묶음에서 `is_last` 이면 `RepeatDraftView(interval_weeks=묶음 간격, count=DEFAULT_COUNT, starts_at=next_start(이 방문의 starts_at, 묶음 간격))`.
  - 보낼 것 묶음: 방문에 묶음이 있으면 `list_series` 에서 예약됨이고 이 방문 이상인 시각들(서로 다른 것, 매장 시간대)과 묶음 간격을 `build_bundle` 에 넘긴다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**
  - 상세: `test_묶음에_든_방문은_간격과_자리를_준다`(4주·3회 중 둘째 → `SeriesBriefView(s, 4, 2, 3, False)`), `test_묶음이_없으면_series_는_None`, `test_가족의_뒤_회차가_취소되면_앞_회차가_마지막이다`(Review Focus 3).
  - 묶음 목록: `test_묶음의_방문을_상태와_상관없이_시각순으로`, `test_다른_매장의_묶음은_404`.
  - 초안: `test_묶음의_마지막_회차면_같은_간격으로_이어_잡을_초안을_준다`(starts_at = 마지막 + 4주 같은 시각, count 6), `test_마지막이_아니면_repeat_는_None`, `test_그_아이에게_뒤_예약이_있으면_upcoming_starts_at`, `test_뒤_예약이_없으면_None`(지금 칸들은 그대로).
  - 보낼 것: `test_반복_묶음의_첫_회차로_부르면_예약_토막에_회차가_전부_있다`(텍스트에 `4주마다 3번 예약했어요` 와 세 줄), `test_둘째_회차로_부르면_그_뒤만`, `test_취소한_회차는_빠진다`.
  - 저장소: `test_next_active_after_는_그_아이들의_뒤_예약_가운데_가장_이른_것`.
- [ ] **Step 2: 실패를 확인한다** — `docker compose run --rm --no-deps backend pytest apps/visit/tests -q -p no:cacheprovider -k "series or draft or send_bundle or get_visit"` → 실패.
- [ ] **Step 3: 구현한다** — 위 Interfaces. 상세는 `visit.series_id` 가 있을 때만 `get`·`list_series` 를 부른다.
- [ ] **Step 4: 통과를 확인한다** — 같은 명령, 단위 전체, `docker compose run --rm backend pytest apps/visit/tests/adapter/test_visit_pg_repository.py -q -p no:cacheprovider` → 통과.
- [ ] **Step 5: 커밋** — `git commit -m "feat(backend): ⑭ 묶음을 읽는 곳 — 방문 상세의 자리, 묶음 목록, 이어 잡기 초안, 보낼 글의 회차 목록"`

### Task 6: `이후 전부` 옮기기·고치기와 변경 안내 한 통

**Files:**
- Create: `backend/apps/visit/app/services/series_scope.py`
- Modify: `reschedule_visits_dto.py`·`_interactor.py`·`_schema.py`·`_router.py`·`_provider.py`, `update_visit_dto.py`·`_interactor.py`·`_schema.py`·`_router.py`·`_provider.py`, `backend/apps/visit/app/dtos/build_send_bundle_dto.py`(`BundlePartView` 를 다시 쓴다), `backend/apps/hub/app/dtos/visit_events.py`(`VisitRescheduled.quiet`), `backend/apps/notification/app/use_cases/handle_visit_event_interactor.py`
- Test: `test_series_scope.py`(app/services), `test_reschedule_visits_interactor.py`, `test_update_visit_interactor.py`, 라우터 둘, notification 인터랙터 테스트

**Interfaces:**
- Consumes: Task 1 `following_of`·`earliest_ids`·`wall_delta`·`wall_shift`·`move_order`·`conflicts_of`·`series_notice`·`SERIES_CHANGE`, Task 2 `list_series`·`active_at`·`move_each`·`VisitSeriesConflictError`.
- Produces:
  - `series_scope.Scope(anchors: list[Visit], targets: list[Visit], series_id: int | None)` 와 `async lock_scope(ctx, visit_ids: Sequence[int], *, following: bool, family: bool, skip_ids: frozenset[int], visits: VisitLookupRepository, directory: CustomerDirectoryPort, pet_ids: tuple[int, ...] = ()) -> Scope`:
    - `following` 이 아니거나 anchors 에 묶음이 없으면 지금의 `lock_visits` 그대로(targets = anchors, series_id None).
    - 아니면: `get_many` → 없으면 `VisitNotFoundError`, 보호자가 여럿이면 `VisitGroupMismatchError`, 묶음·시작 시각이 다르면 `VisitInputError("이후 전부는 한 회차에서만 할 수 있어요.")` → `lock_family` → `list_series` → `following_of` 로 고른 ID ∪ anchors 를 **한 번에** `lock`(ID 오름차순) → 잠근 값으로 `following_of` 를 다시 해 targets. targets 가 비면 `VisitInputError("바꿀 예약이 없어요.")`.
  - 요청 칸(옮기기·고치기·전이 공통): `scope: "this" | "following" = "this"`, `family: bool = true`, `skip_visit_ids: [EntityId] (24 개까지, 중복 없음) = []`. 명령 칸 `scope: str = "this"`, `family: bool = True`, `skip_visit_ids: tuple[int, ...] = ()`.
  - 응답 칸 `notice: [{kind, text}] = []` — `RescheduledVisitsView.notice`, `UpdatedVisitView.notice`(Task 7 에서 `TransitionedVisitsView.notice`).
  - `VisitRescheduled.quiet: bool = False`(`previous_starts_at` 다음, `family_pet_ids` 앞). notification `_rescheduled`: `quiet` 이면 변경 안내(`change`)를 만들지 않는다 — 옛 시각의 줄 거두기와 새 리마인드는 지금처럼.
  - `RescheduleVisitsInteractor(..., shops: ShopProfilePort)`, `UpdateVisitInteractor(..., shops: ShopProfilePort)`(키워드).
- 옮기기(`following`): `check_start(command.starts_at)` → `lock_scope` → anchors 가 모두 예약됨이 아니면 `VisitStateConflictError` → `delta = wall_delta(anchor.starts_at, command.starts_at)` → targets 마다 `wall_shift` 와 `check_same_day(새 시각, 그 방문의 소요)` → `conflicts_of(moves, active_at(새 시각들) 에서 targets 를 뺀 것)` 이 있으면 `VisitSeriesConflictError`(쓰기 없음) → `move_each(move_order(moves))` → 방문마다 `VisitRescheduled(previous_starts_at=옛 시각, quiet = id ∉ earliest_ids(옮기기 전 targets), family_pet_ids = 같은 새 시각의 아이들)` → 방문마다 `SearchSourceChanged` → 경고는 anchor 의 새 시각 → `notice = [series_notice(SERIES_CHANGE, shop_name, 옮긴 방문의 아이 이름(중복 없이, 처음 나온 차례), 새 시각들)]`(매장 프로필이 없으면 빈 목록).
- 고치기(`following`): 반려동물을 바꾸면 `VisitInputError("아이를 바꾸는 것은 이 예약만 할 수 있어요.")` → 고를 수 있는 메뉴 = 쓸 수 있는 메뉴 ∪ anchor 의 지금 메뉴 → 시각 차이가 있으면 위와 같은 걸린 회차 검사 → `move_order` 차례로 targets 마다 `update_details(새 시각, 그 방문의 아이, 소요, 메뉴, 메모)` → 시각이 바뀌었으면 옮기기와 같은 `VisitRescheduled`(quiet) 와 `notice`, 아니면 알림 이벤트·`notice` 없음 → `SearchSourceChanged` 는 늘 방문마다. 응답의 `visit` 은 anchor.

- [ ] **Step 1: 실패하는 테스트를 쓴다**
  - `test_series_scope.py`: `test_이후_전부는_고객_행을_잠근_뒤_대상을_한_번에_ID_순으로_잠근다`(journal: `lock_family` → `lock_visits [ids 오름차순]` 한 번), `test_묶음이_없는_방문의_following_은_this_와_같다`(Review Focus 5), `test_회차가_다른_방문을_함께_보내면_VISIT_INPUT`, `test_잠근_뒤_다시_읽은_상태로_고른다`(잠그기 전에 예약됨이던 넷째 회차가 잠근 값에서 완료면 빠진다 — 가짜의 `lock` 이 그 순간 행을 바꾼다).
  - 옮기기: `test_이후_전부를_같은_차이만큼_민다`(주마다 3회 묶음의 2회차를 하루 뒤 15:00 으로 → 2·3회차가 하루 뒤 15:00, 1회차 그대로), `test_가장_가까운_회차만_변경_안내이고_나머지는_조용히`(이벤트의 quiet `[False, True]`), `test_걸린_회차가_있으면_아무것도_바꾸지_않고_VISIT_SERIES_CONFLICT`(details 의 visit_id·reason `taken`, 가짜의 rows 그대로), `test_범위_밖으로_밀리는_회차는_out_of_range_로_걸린다`(Review Focus 2), `test_skip_visit_ids_로_걸린_회차를_빼고_옮긴다`, `test_family_false_면_그_아이의_뒤_회차만`, `test_미용_중_완료_취소_앞선_회차는_건드리지_않는다`(P14), `test_방문마다_검색_이벤트`, `test_notice_에_옮긴_회차가_전부`, `test_scope_없는_예전_요청은_지금처럼`(notice 빈 목록, quiet 기본값).
  - 고치기: `test_이후_전부_고치기는_메뉴_소요_메모를_같게_한다`, `test_시각을_바꾸면_같은_차이만큼_밀고_안내는_한_통`, `test_시각이_그대로면_알림_이벤트도_notice_도_없다`, `test_이후_전부에서_아이를_바꾸면_VISIT_INPUT`.
  - 라우터: 칸 셋을 명령으로 옮김, `scope` 이 모르는 값이면 422, 409 본문에 `details.conflicts`.
  - notification: `test_조용한_일정_변경은_변경_안내_없이_리마인드만_옮긴다`.
- [ ] **Step 2: 실패를 확인한다** — `docker compose run --rm --no-deps backend pytest apps/visit/tests apps/notification/tests -q -p no:cacheprovider -k "series_scope or reschedule or update_visit or handle_visit_event"` → 실패.
- [ ] **Step 3: 구현한다** — 위 규칙대로. `this` 경로의 코드는 바꾸지 않는다(`lock_scope` 가 `lock_visits` 를 그대로 부른다).
- [ ] **Step 4: 통과를 확인한다** — 같은 명령, 단위 전체, `lint-imports` → 통과.
- [ ] **Step 5: 커밋** — `git commit -m "feat(backend): ⑭ 이후 전부 옮기기·고치기 — 걸린 회차 409, 변경 안내는 가장 가까운 회차 한 통(quiet), 보낼 글"`

### Task 7: `이후 전부` 취소와 취소 안내 한 통

**Files:**
- Modify: `transition_visits_dto.py`·`_interactor.py`·`_schema.py`·`_router.py`·`_provider.py`, `backend/apps/hub/app/dtos/visit_events.py`(`VisitCanceled.quiet`), notification 인터랙터
- Test: `test_transition_visits_interactor.py`, `test_transition_visits_router.py`, notification 인터랙터 테스트

**Interfaces:**
- Consumes: Task 6 `lock_scope`·요청 칸 셋, Task 1 `earliest_ids`·`series_notice`·`SERIES_CANCEL`.
- Produces: `TransitionedVisitsView.notice`, `VisitCanceled.quiet: bool = False`(`reason` 다음, `family_pet_ids` 앞), notification `_canceled`: `quiet` 이면 취소 안내(`cancel`)를 만들지 않는다(대기 줄 거두기는 지금처럼). `TransitionVisitsInteractor(..., shops: ShopProfilePort)`.
- 규칙: `scope=following` 은 `cancel` 에만 — 다른 행동이면 `VisitInputError("이후 전부는 취소에만 쓸 수 있어요.")`. anchors 가 모두 예약됨이어야 한다(아니면 `VisitStateConflictError`). 대상 전부를 지금 전이 길(`transition` → `apply_changes` → `apply_completion_effects`)로 취소. 이벤트는 `VisitCanceled(reason, quiet = id ∉ earliest_ids(targets))`, `family_pet_ids` 는 같은 시각끼리. `notice = [series_notice(SERIES_CANCEL, …, 취소한 시각들)]`.

- [ ] **Step 1: 실패하는 테스트를 쓴다** — `test_이후_전부_취소는_뒤의_예약됨만_취소한다`(가족 묶음에 미용 중·완료·`이 예약만` 취소가 섞임 — Review Focus 3), `test_취소_안내는_가장_가까운_회차_한_통`(quiet `[False, False, True, True]` — 가까운 회차가 가족 둘), `test_notice_에_취소한_회차가_전부`, `test_이후_전부는_취소에만`, `test_scope_없는_예전_요청은_지금처럼`, 라우터 칸 옮김, notification `test_조용한_취소는_취소_안내_없이_대기_줄만_거둔다`.
- [ ] **Step 2: 실패를 확인한다** — `docker compose run --rm --no-deps backend pytest apps/visit/tests apps/notification/tests -q -p no:cacheprovider -k "transition or handle_visit_event"` → 실패.
- [ ] **Step 3: 구현한다**.
- [ ] **Step 4: 통과를 확인한다** — 같은 명령, 단위 전체 → 통과.
- [ ] **Step 5: 커밋** — `git commit -m "feat(backend): ⑭ 이후 전부 취소 — 취소 안내는 가장 가까운 회차 한 통(quiet), 보낼 글"`

### Task 8: 실제 배선·흐름 스크립트·문서

**Files:**
- Create: `backend/tests/integration/test_repeat_wiring.py`, `backend/scripts/check_repeat_flow.sh`, `_docs/decisions/017-pass-recurring.md`
- Modify: `backend/apps/visit/CLAUDE.md`(이벤트 표의 세 줄 — 등록의 `series_followup`, 옮기기·고치기·취소의 `quiet` — 와 ⑭ 반복 예약 절), `backend/apps/notification/CLAUDE.md`(세 칸의 가지), `CLAUDE.md`(명령어에 `check_repeat_flow.sh` 한 줄), `_docs/harness.md`(흐름 표 한 줄)

**Interfaces:**
- Consumes: Task 1~7 전부.

- [ ] **Step 1: 통합 테스트를 쓴다** — `test_repeat_wiring.py`(`pytestmark = pytest.mark.integration`, 첫 테스트는 테넌트 격리):
  - `test_다른_매장의_미리_보기는_403`.
  - `test_가족_6회_반복은_한_묶음이고_알림은_접수_한_통_리마인드_여섯` — `test_notification_subscriber_wiring._link` 와 같은 SQL 로 채널을 잇고 `POST /visits`(가족 둘, 1주·6회, 첫 회차 내일 14:00) → `visits` 열두 줄이 같은 `series_id`, `notification_messages` 의 `confirm` 1·`reminder` 6(가족 묶음 한 통씩), `search_jobs` 의 visit 줄 열둘.
  - `test_주마다_묶음을_이후_전부로_1주_밀어도_된다`(Review Focus 1 — 2회차부터 +7일 → 200, 회차들이 한 주씩 밀림, `change` 줄 하나).
  - `test_걸린_회차가_있으면_409_details_와_아무것도_바뀌지_않음_빼고_다시_보내면_된다` — 묶음 밖 예약을 미리 넣어 두고 → 409 `VISIT_SERIES_CONFLICT`, `details.conflicts[0].reason == "taken"`, DB 의 시각 그대로 → `skip_visit_ids` 로 다시 → 200.
  - `test_이후_전부_취소는_뒤의_예약됨만이고_취소_안내_한_통`(가운데 회차 하나를 미리 `this` 로 취소해 둔다).
  - `test_방문_상세의_묶음_자리와_묶음_목록`.
- [ ] **Step 2: 통합 테스트를 돌린다** — `docker compose run --rm backend pytest tests/integration/test_repeat_wiring.py -q -p no:cacheprovider` → 통과. 실패하면 원인을 고치고(systematic-debugging) 다시.
- [ ] **Step 3: 흐름 스크립트를 쓴다** — `check_repeat_flow.sh`(`check_revisit_flow.sh` 의 도우미 모양, 채널 연동은 `check_notification_flow.sh` 의 토큰 `000000` 단계와 `reregister_templates.py --refresh`): 반복 기본값·미리 보기 → 가족 6번 잡기 → 알림 줄 수(접수 1·리마인드 6) → 보낼 것 묶음에 회차 여섯이 다 있음(글은 찍지 않고 줄 수만) → 이후 전부 옮기기: 걸린 회차 409 → 빼고 진행 → 이후 전부 취소(보낼 글에 회차 전부) → 지난 회차로 시작하는 짧은 묶음(2주 전·1주 전·오늘)의 마지막 회차 완료 → 초안의 `repeat` → 직원도 반복 등록 200. 단계 이름과 판정만 찍는다.
- [ ] **Step 4: 흐름을 돌린다** — `docker compose restart backend` 뒤 `bash ../backend/scripts/check_repeat_flow.sh` → 모든 줄 `통과`. 앞선 흐름 회귀로 `check_visit_flow.sh`·`check_notification_flow.sh`·`check_revisit_flow.sh` 도 통과.
- [ ] **Step 5: 전체 검증** — 단위 전체, 통합 전체, `lint-imports`(계약 6), 라우트 표를 main 의 것과 견준다(새 경로 셋 — `GET /visits/repeat-defaults`·`GET /visits/repeat-preview`·`GET /visit-series/{series_id}` — 만 늘고 로그인 없는 경로는 그대로).
- [ ] **Step 6: 문서를 쓴다** — 결정 기록 017(⑭-1 절: 이 계획의 Rulings 와 실행 중 Ruling), visit·notification `CLAUDE.md`, 루트 `CLAUDE.md` 명령 한 줄, `_docs/harness.md` 한 줄.
- [ ] **Step 7: 커밋** — `git commit -m "test(backend): ⑭ 반복 예약 실제 배선·흐름 스크립트, 결정 기록 017·문서"`
