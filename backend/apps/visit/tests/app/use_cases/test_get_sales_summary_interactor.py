"""매출 요약 — 낱말의 뜻(설계 ⑧ 3.1)을 스텁 포트로 하나씩 본다. 오늘은 2026-11-14 토요일 15:00(서울)이다."""
from datetime import date

import pytest

from visit.app.dtos.get_sales_summary_dto import CompareWindowView, GetSalesSummaryQuery, GoalView
from visit.app.services.pet_cards import PetCard
from visit.app.use_cases.get_sales_summary_interactor import GetSalesSummaryInteractor
from visit.domain.errors import VisitInputError
from visit.domain.value_objects.sales import (
    DaySales,
    DuePet,
    MenuSales,
    PetVisits,
    RemainingBookings,
    SalesTotals,
)
from visit.tests.helpers.builders import ctx, kst, record
from visit.tests.helpers.fakes import (
    FakeDirectory,
    FakeLibrary,
    FakeMenus,
    FakeRecords,
    FakeSalesGoalRepository,
    FakeSalesRepository,
    FakeVisits,
)

NOW = kst(11, 14, 15)
MIDNIGHT = kst(11, 14, 0)     # 오늘 0시(서울) — 오늘의 예약은 시각이 지났어도 '앞으로의 예약'이다
TODAY = date(2026, 11, 14)
NOV = (date(2026, 11, 1), date(2026, 12, 1))
OCT_SAME = (date(2026, 10, 1), date(2026, 10, 15))        # 10월 1~14일 — 끝 다음 날
OCT = (date(2026, 10, 1), date(2026, 11, 1))
SEP = (date(2026, 9, 1), date(2026, 10, 1))
NOV_2025_SAME = (date(2025, 11, 1), date(2025, 11, 15))
YEAR = (date(2026, 1, 1), date(2027, 1, 1))
YEAR_TO_TODAY = (date(2026, 1, 1), date(2026, 11, 15))


class _World:
    def __init__(self, now=NOW):
        self.sales, self.goals, self.menus = FakeSalesRepository(), FakeSalesGoalRepository(), FakeMenus()
        self.directory, self.visits, self.library = FakeDirectory(), FakeVisits(), FakeLibrary()
        self.records = FakeRecords(self.visits)
        self.directory.family(1, pets=tuple(range(101, 121)))
        self.interactor = GetSalesSummaryInteractor(
            sales=self.sales, goals=self.goals, menus=self.menus, directory=self.directory,
            records=self.records, library=self.library, now=lambda: now,
        )

    async def summary(self, span="month", anchor=None, shop_id=1):
        return await self.interactor.get_sales_summary(
            GetSalesSummaryQuery(ctx=ctx(shop_id=shop_id), span=span, anchor=anchor))

    def photo(self, pet_id: int, media_id: int) -> None:
        """그 아이의 프로필 사진 — 사진이 붙은 완료 방문 하나."""
        visit = self.visits.seed(pet_id=pet_id, starts_at=kst(10, 1, 10), status="completed",
                                 started_at=kst(10, 1, 10), completed_at=kst(10, 1, 12))
        self.library.add(media_id, attached=True)
        self.records.seed(record(visit.id, media=((media_id, "photo", "after", 0),)))


def _pet(pet_id, visits=1, last=date(2026, 11, 10), first=date(2026, 1, 5)) -> PetVisits:
    return PetVisits(pet_id=pet_id, visits=visits, last_day=last, first_ever_day=first)


# ---------- 합계와 평균 ----------

async def test_매출과_방문_수와_평균을_준다_평균은_원_단위에서_버린다():
    w = _World()
    w.sales.totals_by[NOV] = SalesTotals(revenue=100_000, completed=4, priced=3, unrecorded=1, no_show=2, canceled=1)
    s = await w.summary()
    assert (s.span, s.revenue, s.visit_count, s.priced_count, s.average) == ("month", 100_000, 4, 3, 33_333)
    assert (s.unrecorded_count, s.bookings.no_show, s.bookings.canceled) == (1, 2, 1)
    assert (s.period.start, s.period.end, s.period.elapsed_end) == (date(2026, 11, 1), date(2026, 11, 30), TODAY)


async def test_총액을_적은_방문이_없으면_평균은_None_이다():
    w = _World()
    w.sales.totals_by[NOV] = SalesTotals(revenue=0, completed=2, priced=0, unrecorded=2, no_show=0, canceled=0)
    assert (await w.summary()).average is None


async def test_anchor_가_없으면_매장_시간대의_오늘이다():
    w = _World(now=kst(11, 1, 0, 30))          # 서울 11월 1일 00:30 — UTC 로는 10월 31일
    w.sales.totals_by[NOV] = SalesTotals(70_000, 1, 1, 0, 0, 0)
    s = await w.summary("month")
    assert (s.period.start, s.revenue, s.period.elapsed_end) == (date(2026, 11, 1), 70_000, date(2026, 11, 1))


@pytest.mark.parametrize("anchor", [date(1999, 12, 31), date(2101, 1, 1)])
async def test_받는_범위_밖의_anchor_는_422_다(anchor):
    with pytest.raises(VisitInputError):
        await _World().summary("month", anchor)


@pytest.mark.parametrize("span,anchor", [("week", date(2100, 12, 31)), ("year", date(2100, 12, 31)),
                                         ("month", date(2000, 1, 1)), ("day", date(2000, 1, 1))])
async def test_범위의_끝에서도_요약이_나온다(span, anchor):
    s = await _World().summary(span, anchor)
    assert s.revenue == 0


# ---------- 결제 수단·메뉴·조정 (Review Focus 4) ----------

async def test_결제_수단은_정해진_순서이고_0원인_수단은_없고_미선택은_none_이다():
    w = _World()
    w.sales.totals_by[NOV] = SalesTotals(90_000, 3, 3, 0, 0, 0)
    w.sales.payments_by[NOV] = {None: 10_000, "transfer": 0, "cash": 30_000, "card": 50_000}
    s = await w.summary()
    assert [(p.method, p.amount) for p in s.payments] == [("card", 50_000), ("cash", 30_000), ("none", 10_000)]
    assert sum(p.amount for p in s.payments) == s.revenue


@pytest.mark.parametrize("revenue,adjustment", [(95_000, 25_000), (60_000, -10_000), (70_000, None)])
async def test_총액이_항목_합과_다르면_조정_한_줄로_합을_맞춘다(revenue, adjustment):
    w = _World()
    full, bath = w.menus.seed("전체 미용"), w.menus.seed("목욕")
    w.sales.totals_by[NOV] = SalesTotals(revenue, 3, 3, 0, 0, 0)
    w.sales.menus_by[NOV] = [MenuSales(full.id, 50_000, 1, 101), MenuSales(bath.id, 20_000, 2, None)]
    s = await w.summary()
    rows = [(m.menu_id, m.name, m.amount, m.count) for m in s.menus]
    expected = [(full.id, "전체 미용", 50_000, 1), (bath.id, "목욕", 20_000, 2)]
    if adjustment is not None:
        expected.append((None, "조정", adjustment, 0))
    assert rows == expected
    assert sum(m.amount for m in s.menus) == s.revenue
    assert (s.menus[0].pet.pet_id, s.menus[1].pet) == (101, None)


async def test_항목이_하나도_없으면_매출_전체가_조정이다():
    w = _World()
    w.sales.totals_by[NOV] = SalesTotals(30_000, 1, 1, 0, 0, 0)
    [only] = (await w.summary()).menus
    assert (only.menu_id, only.name, only.amount) == (None, "조정", 30_000)


async def test_합이_서로_맞는다():
    w = _World()
    full = w.menus.seed("전체 미용")
    w.sales.totals_by[NOV] = SalesTotals(80_000, 3, 2, 1, 0, 0)
    w.sales.payments_by[NOV] = {"card": 30_000, "cash": 50_000}
    w.sales.menus_by[NOV] = [MenuSales(full.id, 75_000, 2, None)]
    w.sales.days_by[NOV] = [DaySales(date(2026, 11, 3), 30_000, 1, ()), DaySales(date(2026, 11, 9), 50_000, 2, ())]
    s = await w.summary()
    assert s.revenue == sum(p.amount for p in s.payments) == sum(m.amount for m in s.menus) \
        == sum(b.revenue for b in s.buckets) == sum(s.weekdays) == 80_000


# ---------- 아이 (Review Focus 3) ----------

async def test_처음_온_아이와_다시_온_아이를_가르고_얼굴은_최근_순_여섯이다():
    w = _World()
    w.sales.pets_by[NOV] = [
        _pet(101, last=date(2026, 11, 13)),
        _pet(102, last=date(2026, 11, 12), first=date(2026, 11, 12)),      # 이번 달에 처음
        _pet(103, last=date(2026, 11, 11)),
        _pet(104, last=date(2026, 11, 10), first=date(2026, 11, 1)),       # 첫날에 처음
        _pet(105, last=date(2026, 11, 9), first=date(2026, 10, 31)),       # 전날에 처음 — 다시 온 아이
        _pet(106, last=date(2026, 11, 8)),
        _pet(107, last=date(2026, 11, 7)),
        _pet(108, last=date(2026, 11, 6), first=date(2026, 11, 6)),
    ]
    s = await w.summary()
    assert (s.pets.count, s.pets.new_count, s.pets.returning_count) == (8, 3, 5)
    assert [p.pet_id for p in s.pets.faces] == [101, 102, 103, 104, 105, 106]
    assert [p.pet_id for p in s.pets.new] == [102, 104, 108]
    assert [p.pet_id for p in s.pets.returning] == [101, 103, 105, 106]
    assert s.pets.faces[0] == PetCard(pet_id=101, name="아이101", photo_url=None)


async def test_익명화하거나_지운_아이는_수에는_들고_얼굴에는_없다():
    w = _World()
    w.directory.pet_names[102] = None                       # 익명화한 고객의 아이
    full = w.menus.seed("전체 미용")
    w.sales.totals_by[NOV] = SalesTotals(50_000, 3, 3, 0, 0, 0)
    w.sales.pets_by[NOV] = [
        _pet(102, visits=5, last=date(2026, 11, 13), first=date(2026, 11, 2)),
        _pet(999, visits=4, last=date(2026, 11, 12)),       # 지운 아이 — 요약에 없다
        _pet(101, visits=1, last=date(2026, 11, 11)),
    ]
    w.sales.pets_by[YEAR_TO_TODAY] = w.sales.pets_by[NOV]
    w.sales.menus_by[NOV] = [MenuSales(full.id, 50_000, 3, 102)]
    w.sales.days_by[NOV] = [DaySales(date(2026, 11, 13), 50_000, 3, (102, 999, 101))]
    s = await w.summary()
    assert (s.pets.count, s.pets.new_count, s.pets.returning_count) == (3, 1, 2)
    assert [p.pet_id for p in s.pets.faces] == [101]
    assert s.pets.new == []
    assert [p.pet_id for p in s.pets.returning] == [101]
    assert [(r.pet.pet_id, r.visit_count) for r in s.regulars] == [(101, 1)]
    assert s.menus[0].pet is None
    assert [p.pet_id for p in s.buckets[12].pets] == [101]
    assert s.revenue == 50_000                              # 돈은 남는다


async def test_무지개다리를_건넌_아이도_다녀간_얼굴에는_나온다():
    w = _World()
    w.directory.family(2, pets=(201,), passed=(201,))
    w.sales.pets_by[NOV] = [_pet(201)]
    assert [p.pet_id for p in (await w.summary()).pets.faces] == [201]


async def test_사진이_있는_아이는_프로필_사진_주소가_오고_없으면_None_이다():
    w = _World()
    w.photo(101, media_id=51)
    w.sales.pets_by[NOV] = [_pet(101, last=date(2026, 11, 13)), _pet(102, last=date(2026, 11, 12))]
    faces = (await w.summary()).pets.faces
    assert faces == [PetCard(101, "아이101", "t/51"), PetCard(102, "아이102", None)]


async def test_다른_매장의_아이는_얼굴에_없다():
    w = _World()
    w.directory.family(5, pets=(501,), shop_id=2)
    w.sales.pets_by[NOV] = [_pet(501)]
    assert (await w.summary()).pets.faces == []


# ---------- 비교 (Review Focus 2) ----------

async def test_진행_중인_달은_같은_날까지의_지난달과_견준다():
    w = _World()
    w.sales.totals_by[NOV] = SalesTotals(3_250_000, 48, 48, 0, 0, 0)
    w.sales.totals_by[OCT_SAME] = SalesTotals(2_830_000, 40, 40, 0, 0, 0)
    w.sales.totals_by[OCT] = SalesTotals(9_999_999, 99, 99, 0, 0, 0)          # 10월 전체가 아니다
    s = await w.summary()
    assert s.compare.previous == CompareWindowView(date(2026, 10, 1), date(2026, 10, 14), 2_830_000)


async def test_지난_달은_그_앞_달_전체와_견준다():
    w = _World()
    w.sales.totals_by[OCT] = SalesTotals(5_000_000, 70, 70, 0, 0, 0)
    w.sales.totals_by[SEP] = SalesTotals(4_000_000, 60, 60, 0, 0, 0)
    s = await w.summary("month", date(2026, 10, 10))
    assert s.compare.previous == CompareWindowView(date(2026, 9, 1), date(2026, 9, 30), 4_000_000)
    assert s.period.elapsed_end == date(2026, 10, 31)


async def test_작년_같은_때는_매출이_있었을_때만_온다():
    w = _World()
    s = await w.summary()
    assert s.compare.year_ago is None
    assert s.compare.previous == CompareWindowView(date(2026, 10, 1), date(2026, 10, 14), 0)   # 앞 기간은 0 이어도 온다
    w.sales.totals_by[NOV_2025_SAME] = SalesTotals(2_000_000, 30, 30, 0, 0, 0)
    s = await w.summary()
    assert s.compare.year_ago == CompareWindowView(date(2025, 11, 1), date(2025, 11, 14), 2_000_000)


async def test_연_보기에는_작년_줄이_따로_없고_앞_기간이_작년이다():
    w = _World()
    w.sales.totals_by[(date(2025, 1, 1), date(2025, 11, 15))] = SalesTotals(30_000_000, 1, 1, 0, 0, 0)
    s = await w.summary("year")
    assert s.compare.year_ago is None
    assert s.compare.previous == CompareWindowView(date(2025, 1, 1), date(2025, 11, 14), 30_000_000)


async def test_앞날의_기간은_빈_요약이고_오류가_아니다():
    w = _World()
    w.goals.rows[1] = 5_000_000
    w.sales.remaining = RemainingBookings(4, 100_000)
    s = await w.summary("month", date(2026, 12, 25))
    assert (s.revenue, s.visit_count, s.average, s.period.elapsed_end) == (0, 0, None, None)
    assert (s.compare.previous, s.compare.year_ago, s.goal, s.report) == (None, None, None, None)
    assert (s.bookings.remaining, s.regulars, s.payments, s.menus) == (None, [], [], [])
    assert len(s.buckets) == 31 and all(b.future and b.revenue == 0 for b in s.buckets)


# ---------- 칸 ----------

async def test_월의_칸은_그_달의_날수만큼이고_오늘_뒤는_future_다():
    w = _World()
    w.sales.days_by[NOV] = [
        DaySales(date(2026, 11, 3), 30_000, 1, (101,)),
        DaySales(date(2026, 11, 14), 50_000, 2, (102, 103)),
    ]
    buckets = (await w.summary()).buckets
    assert len(buckets) == 30
    assert (buckets[2].key, buckets[2].revenue, buckets[2].visit_count, buckets[2].future) == ("2026-11-03", 30_000, 1, False)
    assert [p.pet_id for p in buckets[13].pets] == [102, 103]
    assert (buckets[0].revenue, buckets[0].visit_count, buckets[0].pets) == (0, 0, [])       # 방문 없는 날도 칸이 있다
    assert [b.future for b in buckets[12:16]] == [False, False, True, True]                  # 14일까지는 지난 날


async def test_주의_칸은_월요일부터_일요일까지_7개다():
    w = _World()
    week = (date(2026, 11, 9), date(2026, 11, 16))
    w.sales.days_by[week] = [DaySales(date(2026, 11, 14), 50_000, 2, (101,))]
    s = await w.summary("week")
    assert [b.key for b in s.buckets] == [f"2026-11-{d:02d}" for d in range(9, 16)]
    assert [b.revenue for b in s.buckets] == [0, 0, 0, 0, 0, 50_000, 0]
    assert s.weekdays is None


async def test_연의_칸은_열두_달이고_달마다_더한다():
    w = _World()
    w.sales.days_by[YEAR] = [
        DaySales(date(2026, 1, 5), 10_000, 1, (101,)), DaySales(date(2026, 1, 20), 20_000, 2, (102,)),
        DaySales(date(2026, 11, 3), 40_000, 1, (103,)),
    ]
    s = await w.summary("year")
    assert [b.key for b in s.buckets] == [f"2026-{m:02d}" for m in range(1, 13)]
    assert [(b.revenue, b.visit_count) for b in s.buckets][0] == (30_000, 3)
    assert s.buckets[10].revenue == 40_000
    assert all(b.pets == [] for b in s.buckets)
    assert [b.future for b in s.buckets[9:]] == [False, False, True]                         # 12월은 아직이다
    assert s.weekdays == [10_000, 60_000, 0, 0, 0, 0, 0]                                     # 1/5 월, 1/20 화, 11/3 화


async def test_일_보기에는_칸이_없다():
    s = await _World().summary("day")
    assert (s.buckets, s.weekdays) == ([], None)
    assert (s.period.start, s.period.end) == (TODAY, TODAY)


async def test_요일별은_월과_연에만_있고_월요일부터다():
    w = _World()
    w.sales.days_by[NOV] = [
        DaySales(date(2026, 11, 2), 10_000, 1, ()),      # 월
        DaySales(date(2026, 11, 7), 30_000, 1, ()),      # 토
        DaySales(date(2026, 11, 14), 50_000, 1, ()),     # 토
        DaySales(date(2026, 11, 8), 5_000, 1, ()),       # 일
    ]
    assert (await w.summary()).weekdays == [10_000, 0, 0, 0, 0, 80_000, 5_000]


# ---------- 목표·예약·알림장·단골·다시 올 때 ----------

async def test_목표는_이번_달의_월_보기에만_보인다():
    w = _World()
    assert (await w.summary()).goal is None                                 # 정하지 않았다
    w.goals.rows[1] = 5_000_000
    assert (await w.summary()).goal == GoalView(monthly_amount=5_000_000)
    assert (await w.summary("month", date(2026, 10, 10))).goal is None      # 지난 달
    assert (await w.summary("week")).goal is None
    assert (await w.summary("year")).goal is None
    assert (await w.summary("day")).goal is None


async def test_남은_예약은_진행_중인_기간에만_있고_지금부터_기간_끝까지다():
    w = _World()
    w.sales.remaining = RemainingBookings(count=12, expected_amount=840_000)
    s = await w.summary()
    assert (s.bookings.remaining, s.bookings.expected_amount) == (12, 840_000)
    # 10시 예약을 10시 20분에 아직 시작하지 않았어도 남은 예약이다 — 오늘 0시부터 센다.
    assert w.sales.remaining_args == (MIDNIGHT, date(2026, 12, 1))
    past = await w.summary("month", date(2026, 10, 10))
    assert (past.bookings.remaining, past.bookings.expected_amount) == (None, None)


async def test_정가가_없으면_예상_금액_없이_건수만_온다():
    w = _World()
    w.sales.remaining = RemainingBookings(count=3, expected_amount=None)
    s = await w.summary()
    assert (s.bookings.remaining, s.bookings.expected_amount) == (3, None)


async def test_알림장은_완료_방문이_있을_때만_온다():
    w = _World()
    assert (await w.summary()).report is None
    w.sales.totals_by[NOV] = SalesTotals(100_000, 48, 48, 0, 0, 0)
    w.sales.reports_by[NOV] = (40, 31)
    report = (await w.summary()).report
    assert (report.completed, report.sent, report.opened) == (48, 40, 31)


async def test_단골은_기간이_든_해의_오늘까지에서_자주_온_순_셋이고_같으면_최근에_온_아이다():
    w = _World()
    w.sales.pets_by[YEAR_TO_TODAY] = [
        _pet(101, visits=3, last=date(2026, 9, 1)),
        _pet(102, visits=7, last=date(2026, 5, 1)),
        _pet(103, visits=3, last=date(2026, 10, 1)),
        _pet(104, visits=3, last=date(2026, 10, 1)),
        _pet(105, visits=1, last=date(2026, 11, 13)),
    ]
    s = await w.summary()
    assert [(r.pet.pet_id, r.visit_count) for r in s.regulars] == [(102, 7), (103, 3), (104, 3)]


async def test_지난_해를_보면_그_해의_단골이다():
    w = _World()
    w.sales.pets_by[(date(2025, 1, 1), date(2026, 1, 1))] = [_pet(110, visits=9, last=date(2025, 12, 1))]
    w.sales.pets_by[YEAR_TO_TODAY] = [_pet(101, visits=3)]
    s = await w.summary("month", date(2025, 6, 10))
    assert [r.pet.pet_id for r in s.regulars] == [110]
    year = await w.summary("year", date(2025, 6, 10))          # 연 보기는 그 기간의 아이들에서 고른다
    assert [r.pet.pet_id for r in year.regulars] == [110]


async def test_다시_올_때가_지난_아이의_수는_무지개다리와_익명화와_지운_아이를_뺀_수다():
    w = _World()
    w.directory.family(2, pets=(201, 202), passed=(202,))
    w.directory.pet_names[102] = None
    w.sales.due = [DuePet(101, date(2026, 8, 1)), DuePet(102, date(2026, 8, 2)), DuePet(202, date(2026, 8, 3)),
                   DuePet(999, date(2026, 8, 4)), DuePet(201, date(2026, 8, 5))]
    s = await w.summary("day")
    assert s.due_pet_count == 2
    assert w.sales.due_args == (TODAY, MIDNIGHT)


async def test_요약_한_번의_저장소_호출_수는_방문_수와_상관없다():
    w = _World()
    full = w.menus.seed("전체 미용")
    w.sales.totals_by[NOV] = SalesTotals(1_000_000, 300, 300, 0, 0, 0)
    w.sales.pets_by[NOV] = [_pet(100 + i) for i in range(1, 21)]
    w.sales.menus_by[NOV] = [MenuSales(full.id, 1_000_000, 300, 101)]
    w.sales.days_by[NOV] = [DaySales(date(2026, 11, d), 10_000, 10, (101, 102, 103, 104, 105)) for d in range(1, 15)]
    await w.summary()
    assert sorted(w.sales.calls) == sorted([
        "totals", "by_day", "by_payment", "by_menu", "pets",       # 이 기간
        "pets",                                                    # 단골(올해)
        "due_candidates", "remaining_reserved", "report_counts",
        "totals", "totals",                                        # 앞 기간·작년
    ])
