from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from visit.adapter.inbound.api.v1.read_public_report_router import read_public_report_router
from visit.app.dtos.read_public_report_dto import PublicReportView
from visit.app.dtos.report_view_dto import (
    ReportCoverView,
    ReportMediaView,
    ReportMenuView,
    ReportShopView,
    ReportView,
)
from visit.dependencies.read_public_report_provider import get_read_public_report_use_case
from visit.domain.errors import ReportClosedError, ReportNotFoundError, TooManyReportRequestsError
from core.link_token import make_token
from visit.domain.value_objects.report_settings import ReportSettings
from visit.tests.helpers.api import Recorder, build_app, client, error_of

TOKEN = make_token(bytes(range(16)), bytes(range(32)))
ALL_ON = ReportSettings(link_days=30, show_menus=True, show_shop_info=True, show_weight=True, show_amount=True)
REPORT = ReportView(
    pet_name="콩이", visit_date=date(2026, 9, 23), care_note="눈물 자국",
    media=(ReportMediaView(media_id=52, kind="video", phase="after", hidden=False, width=1920, height=1080,
                           duration_seconds=12, display_url="d/52", thumb_url="t/52", download_url="dl/52"),),
    cover=ReportCoverView(url="t/52", width=1920, height=1080),
    menus=(ReportMenuView(name="목욕", amount=30000), ReportMenuView(name="발톱", amount=None)),
    total_amount=30000, weight_kg=Decimal("3.4"),
    shop=ReportShopView(name="Hiss Haus", phone="02-123-4567", address=None), settings=ALL_ON,
)
EXPIRES_AT = datetime(2026, 10, 23, 15, tzinfo=ZoneInfo("Asia/Seoul"))
FULL = {
    "pet_name": "콩이", "visit_date": "2026-09-23", "care_note": "눈물 자국",
    "media": [{"kind": "video", "phase": "after", "width": 1920, "height": 1080, "duration_seconds": 12,
               "display_url": "d/52", "thumb_url": "t/52", "download_url": "dl/52"}],
    "cover": {"url": "t/52", "width": 1920, "height": 1080},
    "menus": [{"name": "목욕", "amount": 30000}, {"name": "발톱", "amount": None}],
    "total_amount": 30000, "weight_kg": 3.4,
    "shop": {"name": "Hiss Haus", "phone": "02-123-4567", "address": None},
    "expires_at": "2026-10-23T15:00:00+09:00",
}


def _view(**settings) -> PublicReportView:
    """조립 함수가 하듯 끈 항목은 비워 둔 알림장."""
    chosen = ReportSettings(**{**vars(ALL_ON), **settings})
    menus = None if not chosen.show_menus else tuple(
        ReportMenuView(name=m.name, amount=m.amount if chosen.show_amount else None) for m in REPORT.menus)
    report = ReportView(**{
        **vars(REPORT), "settings": chosen, "menus": menus,
        "total_amount": REPORT.total_amount if chosen.show_amount else None,
        "weight_kg": REPORT.weight_kg if chosen.show_weight else None,
        "shop": REPORT.shop if chosen.show_shop_info else None,
    })
    return PublicReportView(report=report, expires_at=EXPIRES_AT)


async def _get(stub, headers=None):
    async with client(build_app(read_public_report_router, get_read_public_report_use_case, stub)) as c:
        return await c.get("/v1/public/report", headers=headers)


async def test_헤더의_토큰으로_알림장을_읽는다_로그인은_없다():
    stub = Recorder(_view())
    response = await _get(stub, {"X-Report-Token": TOKEN})
    assert (response.status_code, response.json()) == (200, FULL)
    assert (stub.calls[0].token, stub.calls[0].client) == (TOKEN, "127.0.0.1")


async def test_검색과_캐시를_막는_헤더를_단다():
    response = await _get(Recorder(_view()), {"X-Report-Token": TOKEN})
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["x-robots-tag"] == "noindex, nofollow"


@pytest.mark.parametrize(("off", "missing"), [
    ({"show_menus": False}, {"menus"}),
    ({"show_amount": False}, {"total_amount"}),
    ({"show_weight": False}, {"weight_kg"}),
    ({"show_shop_info": False}, {"shop"}),
    ({"show_menus": False, "show_amount": False, "show_weight": False, "show_shop_info": False},
     {"menus", "total_amount", "weight_kg", "shop"}),
], ids=["메뉴", "금액", "몸무게", "매장 정보", "전부"])
async def test_끈_항목은_칸이_아예_없다(off, missing):
    """R7"""
    body = (await _get(Recorder(_view(**off)), {"X-Report-Token": TOKEN})).json()
    assert set(FULL) - set(body) == missing
    assert {k: v for k, v in body.items() if k != "menus"} == {
        k: v for k, v in FULL.items() if k not in missing | {"menus"}}


async def test_금액을_끄면_메뉴에는_이름만_있다():
    body = (await _get(Recorder(_view(show_amount=False)), {"X-Report-Token": TOKEN})).json()
    assert body["menus"] == [{"name": "목욕"}, {"name": "발톱"}]


async def test_켰지만_값이_없는_칸은_null_로_나간다():
    view = _view()
    empty = ReportView(**{**vars(view.report), "pet_name": None, "care_note": None, "media": (), "cover": None,
                          "menus": (), "total_amount": None, "weight_kg": None})
    body = (await _get(Recorder(PublicReportView(report=empty, expires_at=None)), {"X-Report-Token": TOKEN})).json()
    assert body == {
        "pet_name": None, "visit_date": "2026-09-23", "care_note": None, "media": [], "cover": None, "menus": [],
        "total_amount": None, "weight_kg": None,
        "shop": {"name": "Hiss Haus", "phone": "02-123-4567", "address": None}, "expires_at": None,
    }


@pytest.mark.parametrize("headers", [
    None,
    {"X-Report-Token": ""},
    {"X-Report-Token": "a" * 42},
    {"X-Report-Token": "a" * 44},
    {"X-Report-Token": "a" * 5000},
    {"X-Report-Token": "알림장".encode()},
    {"X-Report-Token": " "},
    {"X-Report-Token": TOKEN + "="},
    {"X-Report-Token": make_token(bytes(range(16)), bytes(32))},
    {"Authorization": f"Bearer {TOKEN}"},
], ids=["헤더 없음", "빈 값", "42글자", "44글자", "5000글자", "한글", "공백", "패딩", "다른 키", "다른 헤더"])
async def test_이상한_토큰은_그대로_유스케이스에_넘기고_404_를_그대로_낸다(headers):
    """R13 — 형식 검증(422)을 두지 않는다. 판정은 유스케이스가 한다."""
    stub = Recorder(error=ReportNotFoundError("알림장을 찾을 수 없습니다."))
    response = await _get(stub, headers)
    assert error_of(response) == (404, "REPORT_NOT_FOUND")
    assert set(response.json()) == {"code", "message"}
    assert len(stub.calls) == 1


async def test_닫힌_알림장은_410_너무_잦으면_429_이고_본문은_코드와_문구뿐이다():
    for error, expected in ((ReportClosedError("닫힌 알림장입니다."), (410, "REPORT_CLOSED")),
                            (TooManyReportRequestsError("잠시 뒤에"), (429, "TOO_MANY_ATTEMPTS"))):
        response = await _get(Recorder(error=error), {"X-Report-Token": TOKEN})
        assert error_of(response) == expected
        assert set(response.json()) == {"code", "message"}


async def test_토큰을_경로나_질의로는_받지_않는다():
    stub = Recorder(_view())
    async with client(build_app(read_public_report_router, get_read_public_report_use_case, stub)) as c:
        assert (await c.get(f"/v1/public/report/{TOKEN}")).status_code == 404
        assert (await c.get(f"/v1/public/report?token={TOKEN}&x_report_token={TOKEN}")).status_code == 200
    assert [call.token for call in stub.calls] == [None]
