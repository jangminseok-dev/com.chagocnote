from datetime import date, time

from visit.adapter.inbound.api.v1.parse_visit_draft_router import parse_visit_draft_router
from visit.app.dtos.parse_visit_draft_dto import (
    DraftCandidateView,
    DraftGuessView,
    DraftPetView,
    VisitDraftView,
)
from visit.dependencies.parse_visit_draft_provider import get_parse_visit_draft_use_case
from visit.tests.helpers.api import READ_ONLY, STAFF, Recorder, build_app, client, error_of

DRAFT = VisitDraftView(
    date=date(2026, 9, 25), time=time(14, 0),
    customer_candidates=[DraftCandidateView(customer_id=7, name="이수진", phone_masked="010-12··-5678",
                                            pets=[DraftPetView(pet_id=11, name="두부")], matched_pet_ids=[11])],
    pet_ids=[11], menu_ids=[1, 3], guessed=DraftGuessView(date=False, time=True, who=False, menu=False),
)
TEXT = "안녕하세요 두부 내일 2시 목욕 가능할까요?"


def _app(stub, access=None):
    return build_app(parse_visit_draft_router, get_parse_visit_draft_use_case, stub, access)


async def test_카톡_글을_초안으로_돌려준다():
    stub = Recorder(DRAFT)
    async with client(_app(stub, STAFF)) as c:
        response = await c.post("/v1/shops/3/visit-drafts", json={"text": f"  {TEXT}\n"})
    assert response.status_code == 200
    assert response.json() == {
        "date": "2026-09-25", "time": "14:00",
        "customer_candidates": [{"customer_id": 7, "name": "이수진", "phone_masked": "010-12··-5678",
                                 "pets": [{"pet_id": 11, "name": "두부"}], "matched_pet_ids": [11]}],
        "pet_ids": [11], "menu_ids": [1, 3],
        "guessed": {"date": False, "time": True, "who": False, "menu": False},
    }
    assert (stub.calls[0].ctx.shop_id, stub.calls[0].text) == (3, TEXT)   # 앞뒤 공백은 뗀다


async def test_빈_칸은_null_과_빈_목록이다():
    empty = VisitDraftView(date=None, time=None, customer_candidates=[], pet_ids=[], menu_ids=[],
                           guessed=DraftGuessView(date=False, time=False, who=True, menu=False))
    async with client(_app(Recorder(empty))) as c:
        body = (await c.post("/v1/shops/3/visit-drafts", json={"text": "안녕하세요"})).json()
    assert (body["date"], body["time"], body["customer_candidates"], body["pet_ids"]) == (None, None, [], [])


async def test_빈_글_긴_글_제어_문자는_422_이고_글을_되돌려주지_않는다():
    stub = Recorder(DRAFT)
    async with client(_app(stub)) as c:
        for text in ("", "   ", "가" * 1001, "콩이\x00", "콩이\x07"):
            response = await c.post("/v1/shops/3/visit-drafts", json={"text": text})
            assert error_of(response) == (422, "VALIDATION_ERROR"), text
            assert "콩이" not in response.text and "가가" not in response.text
        assert (await c.post("/v1/shops/3/visit-drafts", json={"text": "콩이\n내일"})).status_code == 200   # 줄바꿈은 된다
        assert (await c.post("/v1/shops/3/visit-drafts", json={})).status_code == 422
    assert len(stub.calls) == 1


async def test_reservation_write_가_없으면_403_이고_글을_되돌려주지_않는다():
    stub = Recorder(DRAFT)
    async with client(_app(stub, READ_ONLY)) as c:
        response = await c.post("/v1/shops/3/visit-drafts", json={"text": TEXT})
    assert error_of(response) == (403, "PERMISSION_DENIED")
    assert "두부" not in response.text
    assert stub.calls == []
