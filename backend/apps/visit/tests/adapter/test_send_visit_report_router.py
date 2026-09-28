from datetime import date

import pytest

from visit.adapter.inbound.api.v1.send_visit_report_router import send_visit_report_router
from visit.app.dtos.get_visit_report_dto import VisitReportPreview
from visit.app.dtos.report_view_dto import ReportLinkView, ReportMediaView, ReportView
from visit.dependencies.send_visit_report_provider import get_send_visit_report_use_case
from visit.domain.errors import (
    ReportEmptyError,
    VisitInputError,
    VisitNoRecordYetError,
    VisitNotCompletedError,
    VisitNotFoundError,
)
from visit.domain.value_objects.report_settings import DEFAULT_REPORT_SETTINGS
from visit.tests.helpers.api import READ_ONLY, STAFF, Recorder, build_app, client, error_of
from visit.tests.helpers.builders import kst

MAX_BIGINT = 9_223_372_036_854_775_807
SENT = VisitReportPreview(
    report=ReportView(
        pet_name="콩이", visit_date=date(2026, 9, 23), care_note="눈물 자국",
        media=(ReportMediaView(media_id=52, kind="photo", phase="after", hidden=True, width=3000, height=2000,
                               duration_seconds=None, display_url="d/52", thumb_url="t/52", download_url="dl/52"),),
        cover=None, menus=(), total_amount=None, weight_kg=None, shop=None, settings=DEFAULT_REPORT_SETTINGS,
    ),
    link=ReportLinkView(status="live", url="https://r.example/r/token", expires_at=kst(10, 23, 15),
                        first_viewed_at=None, created_at=kst(9, 23, 15)),
)


async def _put(stub, body, path="/v1/shops/3/visits/4/report", access=None):
    async with client(build_app(send_visit_report_router, get_send_visit_report_use_case, stub, access)) as c:
        return await c.put(path, json=body)


async def test_직원은_알림장을_보내고_미리보기와_같은_모양을_받는다():
    stub = Recorder(SENT)
    response = await _put(stub, {"hidden_media_ids": [52, MAX_BIGINT]}, access=STAFF)
    assert response.status_code == 200
    assert set(response.json()) == {"report", "link", "settings"}
    assert response.json()["link"]["url"] == "https://r.example/r/token"
    assert [(m["media_id"], m["hidden"]) for m in response.json()["report"]["media"]] == [(52, True)]
    assert response.json()["settings"]["link_days"] == 30
    call = stub.calls[0]
    assert (call.ctx.shop_id, call.visit_id, call.hidden_media_ids) == (3, 4, (52, MAX_BIGINT))


async def test_뺄_것이_없으면_빈_배열을_보내고_33개까지_받는다():
    stub = Recorder(SENT)
    assert (await _put(stub, {"hidden_media_ids": []})).status_code == 200
    assert (await _put(stub, {"hidden_media_ids": list(range(1, 34))})).status_code == 200
    assert [len(call.hidden_media_ids) for call in stub.calls] == [0, 33]


async def test_기록_권한이_없으면_보내지_못한다():
    stub = Recorder(SENT)
    assert error_of(await _put(stub, {"hidden_media_ids": []}, access=READ_ONLY)) == (403, "PERMISSION_DENIED")
    assert stub.calls == []


@pytest.mark.parametrize("body", [
    {}, {"hidden_media_ids": None}, {"hidden_media_ids": 52}, {"hidden_media_ids": "52"},
    {"hidden_media_ids": {"52": True}}, {"hidden_media_ids": ["52"]}, {"hidden_media_ids": [52.0]},
    {"hidden_media_ids": [1.5]}, {"hidden_media_ids": [True]}, {"hidden_media_ids": [None]},
    {"hidden_media_ids": [[52]]}, {"hidden_media_ids": [0]}, {"hidden_media_ids": [-1]},
    {"hidden_media_ids": [MAX_BIGINT + 1]}, {"hidden_media_ids": [52, "가" * 5000]},
    {"hidden_media_ids": list(range(1, 35))}, {"hidden_media_ids": list(range(1, 5001))},
    [52], "52", None,
], ids=lambda body: str(body)[:40])
async def test_뺄_목록이_빠졌거나_정수가_아니거나_범위_밖이거나_33개를_넘으면_422_다(body):
    """R14"""
    stub = Recorder(SENT)
    assert error_of(await _put(stub, body)) == (422, "VALIDATION_ERROR")
    assert stub.calls == []


@pytest.mark.parametrize("visit_id", ["9223372036854775808", "0", "-1", "1.5", "abc", "1" * 400])
async def test_방문_ID_가_범위_밖이거나_숫자가_아니면_422_다(visit_id):
    stub = Recorder(SENT)
    response = await _put(stub, {"hidden_media_ids": []}, f"/v1/shops/3/visits/{visit_id}/report")
    assert error_of(response) == (422, "VALIDATION_ERROR")
    assert stub.calls == []


@pytest.mark.parametrize("error, expected", [
    (VisitNotFoundError("없음"), (404, "VISIT_NOT_FOUND")),
    (VisitNotCompletedError("완료 전"), (409, "VISIT_NOT_COMPLETED")),
    (VisitNoRecordYetError("기록 없음"), (409, "VISIT_NO_RECORD_YET")),
    (ReportEmptyError("빈 알림장"), (422, "REPORT_EMPTY")),
    (VisitInputError("남의 미디어"), (422, "VALIDATION_ERROR")),
])
async def test_도메인_거절은_코드로_나간다(error, expected):
    assert error_of(await _put(Recorder(error=error), {"hidden_media_ids": []})) == expected
