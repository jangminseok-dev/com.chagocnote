from datetime import date

from fastapi import FastAPI

from core.http_errors import install_error_handlers
from search.adapter.inbound.api.error_map import SEARCH_ERROR_STATUS
from search.adapter.inbound.api.v1.search_myself_router import search_myself_router
from search.adapter.inbound.api.v1.search_records_router import search_records_router
from search.app.dtos.search_myself_dto import SearchMyselfResponse
from search.app.dtos.search_records_dto import SearchItemView, SearchResultView
from search.dependencies.search_myself_provider import get_search_myself_use_case
from search.dependencies.search_records_provider import get_search_records_use_case
from search.domain.errors import SearchQueryError
from search.tests.helpers.api import STAFF, Recorder, build_app, client, error_of

SECRET = "귀를 만지면 무는 아이"

RESULT = SearchResultView(semantic=True, items=[
    SearchItemView(kind="care_note", customer_id=1, owner_name="김민지", pet_id=101, pet_name="콩이", photo="thumb-51",
                   visit_id=7, open_pet_id=None, date=date(2026, 11, 3), snippet="발톱을 짧게 깎았어요"),
    SearchItemView(kind="customer_memo", customer_id=2, owner_name="이수진", pet_id=None, pet_name=None, photo=None,
                   visit_id=None, open_pet_id=201, date=None, snippet="문자 선호"),
])


def _app(stub, access=STAFF):
    return build_app(search_records_router, get_search_records_use_case, stub, access)


async def test_직원도_찾고_칸은_정해진_것뿐이다():
    stub = Recorder(RESULT)
    async with client(_app(stub)) as c:
        response = await c.get("/v1/shops/3/search", params={"q": "발톱", "pet_id": 101})
    assert response.status_code == 200
    assert response.json() == {"semantic": True, "items": [
        {"kind": "care_note", "owner": {"customer_id": 1, "name": "김민지"},
         "pet": {"pet_id": 101, "name": "콩이", "photo": "thumb-51"}, "visit_id": 7, "open_pet_id": None,
         "date": "2026-11-03", "snippet": "발톱을 짧게 깎았어요"},
        {"kind": "customer_memo", "owner": {"customer_id": 2, "name": "이수진"}, "pet": None, "visit_id": None,
         "open_pet_id": 201, "date": None, "snippet": "문자 선호"},
    ]}
    [query] = stub.calls
    assert (query.ctx.shop_id, query.q, query.pet_id) == (3, "발톱", 101)


async def test_검색어를_받은_그대로_유스케이스에_넘긴다():
    stub = Recorder(SearchResultView(items=[], semantic=False))
    async with client(_app(stub)) as c:
        response = await c.get("/v1/shops/3/search", params={"q": "  귀 청소  "})
    assert response.json() == {"items": [], "semantic": False}
    assert (stub.calls[0].q, stub.calls[0].pet_id) == ("  귀 청소  ", None)


async def test_검색어가_없거나_너무_길거나_아이_번호가_틀리면_422_이고_입력이_본문에_없다():
    stub = Recorder(RESULT)
    async with client(_app(stub)) as c:
        missing = await c.get("/v1/shops/3/search")
        huge = await c.get("/v1/shops/3/search", params={"q": SECRET * 60})
        bad_pet = await c.get("/v1/shops/3/search", params={"q": SECRET, "pet_id": "abc"})
        zero_pet = await c.get("/v1/shops/3/search", params={"q": SECRET, "pet_id": 0})
    for response in (missing, huge, bad_pet, zero_pet):
        assert error_of(response) == (422, "VALIDATION_ERROR")
        assert "귀를" not in response.text
    assert stub.calls == []


async def test_다듬은_검색어가_규칙에_어긋나면_422_이고_입력이_본문에_없다():
    stub = Recorder(error=SearchQueryError("검색어는 2자에서 100자까지 적어 주세요."))
    async with client(_app(stub)) as c:
        response = await c.get("/v1/shops/3/search", params={"q": SECRET})
    assert error_of(response) == (422, "VALIDATION_ERROR")
    assert "귀를" not in response.text


async def test_로그인이_없으면_401_이다():
    app = FastAPI()
    app.include_router(search_records_router)
    install_error_handlers(app, SEARCH_ERROR_STATUS)
    async with client(app) as c:
        response = await c.get("/v1/shops/3/search", params={"q": "발톱"})
    assert response.status_code == 401


async def test_멤버는_자기소개를_본다():
    stub = Recorder(SearchMyselfResponse(id=9, name="기록 검색 (search)", introduction="소개"))
    async with client(build_app(search_myself_router, get_search_myself_use_case, stub, STAFF)) as c:
        response = await c.get("/v1/shops/3/search/myself")
    assert response.json() == {"id": 9, "name": "기록 검색 (search)", "introduction": "소개"}
    assert stub.calls[0].id == 9
