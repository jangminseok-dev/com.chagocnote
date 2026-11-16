"""알림장 조립 — 켠 항목과 빼지 않은 사진만 담는다(설계 6.3, 위협 점검표 R6·R7)."""
from dataclasses import fields, replace
from datetime import date
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from hub.app.dtos.shop_profile import ShopProfile
from visit.app.dtos.report_view_dto import (
    ReportCoverView,
    ReportLinkView,
    ReportMediaView,
    ReportMenuView,
    ReportShopView,
    ReportView,
)
from visit.app.services.report_reader import describe_link, describe_report
from visit.domain.entities.visit_record import RecordItem
from visit.domain.entities.visit_report import VisitReport
from visit.domain.services.report_rules import hide
from core.link_token import read_token
from visit.domain.value_objects.report_settings import ReportSettings
from visit.tests.helpers.builders import ctx, kst, record, visit
from visit.tests.helpers.fakes import FakeDirectory, FakeLibrary, FakeMenus

SHOP = ShopProfile(shop_id=1, name="Hiss Haus", phone="02-123-4567", address="서울 마포구", timezone="Asia/Seoul",
                   open=True)
KEY = bytes(range(32))


def _settings(menus=False, shop=False, weight=False, amount=False) -> ReportSettings:
    return ReportSettings(link_days=30, show_menus=menus, show_shop_info=shop, show_weight=weight,
                          show_amount=amount)


ALL_ON = _settings(menus=True, shop=True, weight=True, amount=True)
VISIT = visit(status="completed", starts_at=kst(9, 23, 14), memo="SECRET-예약메모", menu_ids=(1,))
# 보이는 순서는 후(52 → 53 → 61) → 전(51) 이다. 61 은 영상.
RECORD = record(
    1, media=((51, "photo", "before", 0), (52, "photo", "after", 0), (53, "photo", "after", 1),
              (61, "video", "after", 2)),
    weight_kg=Decimal("3.4"), care_note="눈물 자국을 닦았어요", internal_note="SECRET-내부메모",
    payment_method="SECRET-결제수단", total_amount=55000, items=(RecordItem(1, 30000), RecordItem(2, 25000)),
)


def _hiding(*media_ids):
    return replace(RECORD, media=hide(RECORD, media_ids))


async def _describe(settings=ALL_ON, a_visit=VISIT, a_record=RECORD, include_hidden=False, pet_names=None,
                    pets=(101,)):
    menus, directory, library = FakeMenus(), FakeDirectory(), FakeLibrary()
    menus.seed("목욕")
    menus.seed("가위컷")
    directory.family(1, pets=pets, name="SECRET-보호자")
    directory.pet_names = pet_names or {}
    for media in RECORD.media:
        library.add(media.media_id, kind=media.kind, attached=True)
    return await describe_report(ctx(), a_visit, a_record, settings, SHOP, menus, directory, library,
                                 include_hidden=include_hidden)


async def test_넷_다_켜면_메뉴와_금액과_몸무게와_매장_정보를_담는다():
    view = await _describe(ALL_ON)
    assert view.menus == (ReportMenuView(name="목욕", amount=30000), ReportMenuView(name="가위컷", amount=25000))
    assert (view.total_amount, view.weight_kg) == (55000, Decimal("3.4"))
    assert view.shop == ReportShopView(name="Hiss Haus", phone="02-123-4567", address="서울 마포구")
    assert view.settings == ALL_ON


async def test_넷_다_꺼도_이름과_날짜와_케어_메모와_사진은_담는다():
    view = await _describe(_settings())
    assert (view.menus, view.total_amount, view.weight_kg, view.shop) == (None, None, None, None)
    assert (view.pet_name, view.visit_date, view.care_note) == ("아이101", date(2026, 9, 23), "눈물 자국을 닦았어요")
    assert [m.media_id for m in view.media] == [52, 53, 61, 51]
    assert view.settings == _settings()


@pytest.mark.parametrize(("settings", "menus", "total"), [
    (_settings(amount=True), None, 55000),
    (_settings(menus=True), (ReportMenuView(name="목욕", amount=None), ReportMenuView(name="가위컷", amount=None)),
     None),
], ids=["메뉴_끔_금액_켬", "메뉴_켬_금액_끔"])
async def test_메뉴와_금액은_따로_켜고_끈다(settings, menus, total):
    view = await _describe(settings)
    assert (view.menus, view.total_amount) == (menus, total)


@pytest.mark.parametrize(("settings", "weight", "shop"), [
    (_settings(weight=True), Decimal("3.4"), None),
    (_settings(shop=True), None, ReportShopView(name="Hiss Haus", phone="02-123-4567", address="서울 마포구")),
], ids=["몸무게만", "매장_정보만"])
async def test_몸무게와_매장_정보도_따로_켜고_끈다(settings, weight, shop):
    view = await _describe(settings)
    assert (view.weight_kg, view.shop) == (weight, shop)


async def test_방문_날짜는_매장_시간대의_날짜다():
    view = await _describe(a_visit=replace(VISIT, starts_at=kst(9, 24, 0, 30)))   # UTC 로는 23일 15:30
    assert view.visit_date == date(2026, 9, 24)


async def test_뺀_사진은_담지_않는다():
    view = await _describe(a_record=_hiding(52, 61))
    assert [(m.media_id, m.hidden) for m in view.media] == [(53, False), (51, False)]


async def test_미리보기는_뺀_사진도_같은_순서에_표시와_함께_담는다():
    view = await _describe(a_record=_hiding(52, 61), include_hidden=True)
    assert [(m.media_id, m.hidden) for m in view.media] == [(52, True), (53, False), (61, True), (51, False)]


async def test_사진은_표시용_영상은_원본_주소를_준다():
    view = await _describe()
    assert view.media[0] == ReportMediaView(
        media_id=52, kind="photo", phase="after", hidden=False, width=3000, height=2000, duration_seconds=None,
        display_url="d/52", thumb_url="t/52", download_url="dl/52")
    assert view.media[2] == ReportMediaView(
        media_id=61, kind="video", phase="after", hidden=False, width=3000, height=2000, duration_seconds=30,
        display_url="o/61", thumb_url="t/61", download_url="dl/61")


@pytest.mark.parametrize("include_hidden", [False, True])
@pytest.mark.parametrize(("hidden", "cover"), [
    ((), "d/52"),
    ((52,), "d/53"),              # 뺀 후 사진을 건너뛴다
    ((52, 53), "d/51"),           # 후 사진이 없으면 전 사진
    ((51, 52, 53), "t/61"),       # 사진이 없으면 영상의 포스터
    ((51, 52, 53, 61), None),
])
async def test_대표는_빼지_않은_것_가운데서_고른다(hidden, cover, include_hidden):
    view = await _describe(a_record=_hiding(*hidden), include_hidden=include_hidden)
    assert view.cover == (ReportCoverView(url=cover, width=3000, height=2000) if cover else None)


async def test_보호자만의_방문은_반려동물_이름이_없다():
    """스텁에 ID 가 None 인 아이를 넣어 둔다 — 없는 ID 로 이름을 묻지 않는다."""
    view = await _describe(a_visit=replace(VISIT, pet_id=None), pets=(None,))
    assert view.pet_name is None


@pytest.mark.parametrize(("a_visit", "pet_names"), [
    (VISIT, {101: None}),                    # 익명화한 고객의 아이 — 틀은 오지만 이름이 없다
    (replace(VISIT, pet_id=999), None),      # 지워진 아이 — 틀도 오지 않는다
], ids=["익명화", "지워진_아이"])
async def test_이름을_얻지_못하면_반려동물_이름이_없다(a_visit, pet_names):
    view = await _describe(a_visit=a_visit, pet_names=pet_names)
    assert view.pet_name is None


@pytest.mark.parametrize("care_note", [None, "", "  \n "])
async def test_몸무게와_메모가_없으면_켜져_있어도_비어_있다(care_note):
    view = await _describe(a_record=replace(RECORD, weight_kg=None, care_note=care_note, items=(), media=()))
    assert (view.weight_kg, view.care_note, view.menus, view.media, view.cover) == (None, None, (), (), None)


@pytest.mark.parametrize("include_hidden", [False, True])
async def test_내부_메모와_결제_수단과_예약_메모와_보호자_정보는_어디에도_없다(include_hidden):
    """R6 — 스텁의 보호자 전화는 010-12··-5678 이다."""
    view = await _describe(ALL_ON, include_hidden=include_hidden)
    assert "SECRET" not in repr(view) and "010-12" not in repr(view)


def test_알림장에는_정해_둔_칸만_있다():
    assert [f.name for f in fields(ReportView)] == [
        "pet_name", "visit_date", "care_note", "media", "cover", "menus", "total_amount", "weight_kg", "shop",
        "settings", "review_url", "review_text"]


def _report(**overrides) -> VisitReport:
    found = dict(id=1, visit_id=1, public_id=bytes(range(16)), expires_at=kst(10, 23, 15), revoked_at=None,
                 first_viewed_at=kst(9, 23, 18), created_by_member_id=11, created_at=kst(9, 23, 15))
    return VisitReport(**{**found, **overrides})


def test_링크가_없으면_상태만_none_이다():
    assert describe_link(None, KEY, "https://r.example") == ReportLinkView(
        status="none", url=None, expires_at=None, first_viewed_at=None, created_at=None)


def test_링크의_주소는_웹_주소와_서명한_토큰_43글자다():
    link = describe_link(_report(), KEY, "https://r.example")
    token = link.url.removeprefix("https://r.example/r/")
    assert (len(token), read_token(token, KEY)) == (43, bytes(range(16)))
    assert read_token(token, bytes(32)) is None
    assert (link.status, link.expires_at, link.first_viewed_at, link.created_at) == (
        "live", kst(10, 23, 15), kst(9, 23, 18), kst(9, 23, 15))


def test_기간이_없고_아직_열지_않은_링크는_그_칸이_비어_있다():
    link = describe_link(_report(expires_at=None, first_viewed_at=None), KEY, "https://r.example")
    assert (link.status, link.expires_at, link.first_viewed_at) == ("live", None, None)


def test_링크의_시각을_매장_시간대로_바꾼다():
    seoul = ZoneInfo("Asia/Seoul")
    link = describe_link(_report(first_viewed_at=None), KEY, "https://r.example").in_zone(seoul)
    assert (link.expires_at.isoformat(), link.first_viewed_at, link.created_at.isoformat()) == (
        "2026-10-23T15:00:00+09:00", None, "2026-09-23T15:00:00+09:00")
    assert describe_link(None, KEY, "https://r.example").in_zone(seoul).expires_at is None
