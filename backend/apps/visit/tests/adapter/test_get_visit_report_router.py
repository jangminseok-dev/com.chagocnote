from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from visit.adapter.inbound.api.v1.get_visit_report_router import get_visit_report_router
from visit.app.dtos.get_visit_report_dto import VisitReportPreview
from visit.app.dtos.report_view_dto import (
    ReportCoverView,
    ReportLinkView,
    ReportMediaView,
    ReportMenuView,
    ReportShopView,
    ReportView,
)
from visit.dependencies.get_visit_report_provider import get_get_visit_report_use_case
from visit.domain.errors import VisitNoRecordYetError, VisitNotFoundError
from visit.domain.value_objects.report_settings import ReportSettings
from visit.tests.helpers.api import READ_ONLY, Recorder, build_app, client, error_of

SEOUL = ZoneInfo("Asia/Seoul")
NO_LINK = ReportLinkView(status="none", url=None, expires_at=None, first_viewed_at=None, created_at=None)
SENT = VisitReportPreview(
    report=ReportView(
        pet_name="콩이", visit_date=date(2026, 9, 23), care_note="눈물 자국",
        media=(ReportMediaView(media_id=52, kind="photo", phase="after", hidden=True, width=3000, height=2000,
                               duration_seconds=None, display_url="d/52", thumb_url="t/52", download_url="dl/52"),),
        cover=ReportCoverView(url="d/52", width=3000, height=2000),
        menus=(ReportMenuView(name="목욕", amount=30000),), total_amount=30000, weight_kg=Decimal("3.4"),
        shop=ReportShopView(name="Hiss Haus", phone="02-123-4567", address=None),
        settings=ReportSettings(link_days=7, show_menus=True, show_shop_info=True, show_weight=True,
                                show_amount=True),
    ),
    link=ReportLinkView(status="live", url="https://r.example/r/token",
                        expires_at=datetime(2026, 9, 30, 15, tzinfo=SEOUL), first_viewed_at=None,
                        created_at=datetime(2026, 9, 23, 15, tzinfo=SEOUL)),
)
HIDDEN = VisitReportPreview(
    report=ReportView(
        pet_name=None, visit_date=date(2026, 9, 23), care_note=None, media=(), cover=None, menus=None,
        total_amount=None, weight_kg=None, shop=None,
        settings=ReportSettings(link_days=None, show_menus=False, show_shop_info=False, show_weight=False,
                                show_amount=False),
    ),
    link=NO_LINK,
)


async def _get(stub, path="/v1/shops/3/visits/1/report", access=None):
    async with client(build_app(get_visit_report_router, get_get_visit_report_use_case, stub, access)) as c:
        return await c.get(path)


async def test_권한이_없는_멤버도_알림장을_미리_본다():
    stub = Recorder(SENT)
    response = await _get(stub, access=READ_ONLY)
    assert response.status_code == 200
    assert response.json() == {
        "report": {
            "pet_name": "콩이", "visit_date": "2026-09-23", "care_note": "눈물 자국",
            "media": [{"media_id": 52, "kind": "photo", "phase": "after", "hidden": True, "width": 3000,
                       "height": 2000, "duration_seconds": None, "display_url": "d/52", "thumb_url": "t/52",
                       "download_url": "dl/52"}],
            "cover": {"url": "d/52", "width": 3000, "height": 2000},
            "menus": [{"name": "목욕", "amount": 30000}], "total_amount": 30000, "weight_kg": 3.4,
            "shop": {"name": "Hiss Haus", "phone": "02-123-4567", "address": None},
        },
        "link": {"status": "live", "url": "https://r.example/r/token", "expires_at": "2026-09-30T15:00:00+09:00",
                 "first_viewed_at": None, "created_at": "2026-09-23T15:00:00+09:00"},
        "settings": {"link_days": 7, "show_menus": True, "show_shop_info": True, "show_weight": True,
                     "show_amount": True},
    }
    assert (stub.calls[0].ctx.shop_id, stub.calls[0].visit_id) == (3, 1)


async def test_끈_항목의_칸은_null_이다():
    body = (await _get(Recorder(HIDDEN))).json()
    assert body["report"] == {
        "pet_name": None, "visit_date": "2026-09-23", "care_note": None, "media": [], "cover": None,
        "menus": None, "total_amount": None, "weight_kg": None, "shop": None,
    }
    assert body["link"] == {"status": "none", "url": None, "expires_at": None, "first_viewed_at": None,
                            "created_at": None}
    assert body["settings"] == {"link_days": None, "show_menus": False, "show_shop_info": False,
                                "show_weight": False, "show_amount": False}


async def test_없는_방문은_404_기록이_없으면_409_다():
    assert error_of(await _get(Recorder(error=VisitNotFoundError("없음")))) == (404, "VISIT_NOT_FOUND")
    assert error_of(await _get(Recorder(error=VisitNoRecordYetError("없음")))) == (409, "VISIT_NO_RECORD_YET")


@pytest.mark.parametrize("visit_id", ["9223372036854775808", "0", "-1", "1.5", "abc", "1" * 400])
async def test_방문_ID_가_범위_밖이거나_숫자가_아니면_422_다(visit_id):
    stub = Recorder(SENT)
    assert error_of(await _get(stub, f"/v1/shops/3/visits/{visit_id}/report")) == (422, "VALIDATION_ERROR")
    assert stub.calls == []
