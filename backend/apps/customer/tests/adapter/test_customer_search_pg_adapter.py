import base64
import json

import pytest
from sqlalchemy import text

from customer.adapter.outbound.pg.customer_pg_repository import CustomerPgRepository
from customer.adapter.outbound.pg.customer_search_pg_adapter import CustomerSearchPgAdapter
from customer.adapter.outbound.pg.pet_pg_repository import PetPgRepository
from customer.app.dtos.customer_search_dto import SearchRequest
from customer.domain.errors import CustomerInputError
from customer.domain.services.search_terms import parse_query
from customer.tests.helpers.profiles import ctx, customer_profile, pet_profile

pytestmark = pytest.mark.integration

A, B = ctx(shop_id=1), ctx(shop_id=2)


async def _family(session, name, phone, pets, shop=A):
    """가족 하나를 넣고 검색 줄을 만든다. 유스케이스가 하는 순서 그대로다."""
    customer = await CustomerPgRepository(session).create(shop, customer_profile(name=name, phone=phone))
    for pet_name in pets:
        await PetPgRepository(session).add(shop, customer.id, pet_profile(name=pet_name))
    await CustomerSearchPgAdapter(session).rebuild_search_entry(shop, customer.id)
    return customer.id


async def _find(session, q, shop=A, sort="recent", include_passed=False, cursor=None, limit=30):
    page = await CustomerSearchPgAdapter(session).search(
        shop, SearchRequest(words=parse_query(q), sort=sort, include_passed=include_passed,
                            cursor=cursor, limit=limit),
    )
    return page


async def _ids(session, q, **kwargs):
    return (await _find(session, q, **kwargs)).customer_ids


async def test_검색_줄은_원본에서_만든다(db_session):
    customer_id = await _family(db_session, "김민지", "01012345678", ["콩이", "두부"])
    row = (await db_session.execute(text(
        "SELECT shop_id, terms, phone_last4, sort_name FROM customer_search_entries WHERE customer_id = :id"
    ), {"id": customer_id})).one()
    assert tuple(row) == (1, "김민지 ㄱㅁㅈ 콩이 ㅋㅇ 두부 ㄷㅂ 01012345678", "5678", "김민지")


async def test_뒷자리가_같은_가족을_모두_찾는다(db_session):
    first = await _family(db_session, "김민지", "01012345678", ["콩이"])
    second = await _family(db_session, "박서준", "01098765678", ["보리"])
    await _family(db_session, "이하나", "01011112222", ["구름"])
    assert set(await _ids(db_session, "5678")) == {first, second}
    assert set(await _ids(db_session, "56")) == {first, second}   # 뒷자리를 앞에서부터 치는 중
    assert await _ids(db_session, "1234-5678") == [first]          # 다섯 자리 이상은 전체 번호 부분 일치


async def test_이름_초성_여러_낱말로_찾는다(db_session):
    kong = await _family(db_session, "김민지", "01012345678", ["콩이", "두부"])
    await _family(db_session, "박서준", "01098765678", ["콩떡"])
    assert await _ids(db_session, "두부") == [kong]
    assert await _ids(db_session, "ㄱㅁㅈ") == [kong]
    assert await _ids(db_session, "ㅋㅇ") == [kong]
    assert await _ids(db_session, "5678 콩이") == [kong]      # 모든 낱말이 걸려야 한다
    assert await _ids(db_session, "민지 ㄷㅂ") == [kong]
    assert await _ids(db_session, "5678 없는이름") == []


async def test_LIKE_특수_문자는_글자_그대로_찾는다(db_session):
    percent = await _family(db_session, "100%보호자", "01012345678", ["콩이"])
    await _family(db_session, "김민지", "01098765678", ["두부"])
    under = await _family(db_session, "a_b", "01011112222", ["보리"])
    assert await _ids(db_session, "%") == [percent]
    assert await _ids(db_session, "_") == [under]
    assert await _ids(db_session, "\\") == []


async def test_다른_매장의_가족은_찾지_않는다(db_session):
    await _family(db_session, "김민지", "01012345678", ["콩이"], shop=B)
    assert await _ids(db_session, "콩이") == []
    assert await _ids(db_session, "") == []


async def test_익명화하면_검색_줄이_지워진다(db_session):
    customer_id = await _family(db_session, "김민지", "01012345678", ["콩이"])
    await CustomerPgRepository(db_session).anonymize(A, customer_id)
    await CustomerSearchPgAdapter(db_session).rebuild_search_entry(A, customer_id)
    assert (await db_session.execute(text("SELECT count(*) FROM customer_search_entries"))).scalar_one() == 0


async def test_다른_매장_컨텍스트로는_검색_줄을_지우지도_만들지도_못한다(db_session):
    customer_id = await _family(db_session, "김민지", "01012345678", ["콩이"])
    await CustomerSearchPgAdapter(db_session).rebuild_search_entry(B, customer_id)
    assert await _ids(db_session, "콩이") == [customer_id]


async def test_반려동물이_모두_무지개다리인_가족은_기본에서_빠진다(db_session):
    customer_id = await _family(db_session, "김민지", "01012345678", ["콩이"])
    pet_id = (await PetPgRepository(db_session).list_for_customers(A, [customer_id]))[0].id
    await PetPgRepository(db_session).set_passed_away(A, pet_id, True)
    assert await _ids(db_session, "") == []
    assert await _ids(db_session, "", include_passed=True) == [customer_id]


async def test_반려동물_수는_검색과_무지개다리를_따른다(db_session):
    adapter = CustomerSearchPgAdapter(db_session)
    kong = await _family(db_session, "김민지", "01012345678", ["콩이", "두부"])
    await _family(db_session, "박서준", "01098765678", ["보리"])
    dubu = (await PetPgRepository(db_session).list_for_customers(A, [kong]))[1].id
    await PetPgRepository(db_session).set_passed_away(A, dubu, True)
    assert await adapter.count_pets(A, parse_query(""), include_passed=False) == 2
    assert await adapter.count_pets(A, parse_query(""), include_passed=True) == 3
    assert await adapter.count_pets(A, parse_query("5678 콩"), include_passed=False) == 1   # 콩이만 (두부는 무지개다리)
    assert await adapter.count_pets(B, parse_query(""), include_passed=True) == 0


async def test_가나다순과_최근순으로_커서를_따라_끝까지_읽는다(db_session):
    names = ["다현", "가은", "나래", "라희", "마루"]
    ids = {}
    for index, name in enumerate(names):
        ids[name] = await _family(db_session, name, f"0101234{index:04d}", ["콩이"])
        await db_session.execute(text(
            "UPDATE customer_search_entries SET last_activity_at = now() - make_interval(mins => :m) "
            "WHERE customer_id = :id"
        ), {"m": 10 - index, "id": ids[name]})

    async def read_all(sort):
        seen, cursor = [], None
        while True:
            page = await _find(db_session, "", sort=sort, cursor=cursor, limit=2)
            seen += page.customer_ids
            if page.next_cursor is None:
                return seen
            cursor = page.next_cursor

    assert await read_all("name") == [ids[n] for n in ["가은", "나래", "다현", "라희", "마루"]]
    assert await read_all("recent") == [ids[n] for n in reversed(names)]


async def test_같은_정렬_값이면_ID_로_이어서_빠지거나_겹치지_않는다(db_session):
    ids = [await _family(db_session, "같은이름", f"0101234{i:04d}", ["콩이"]) for i in range(3)]
    first = await _find(db_session, "", sort="name", limit=2)
    second = await _find(db_session, "", sort="name", cursor=first.next_cursor, limit=2)
    assert first.customer_ids + second.customer_ids == ids
    assert second.next_cursor is None


@pytest.mark.parametrize("cursor", ["", "not-base64!", "WzEsMiwzXQ", "eyJhIjoxfQ"])
async def test_엉터리_커서는_VALIDATION_ERROR_다(db_session, cursor):
    with pytest.raises(CustomerInputError):
        await _find(db_session, "", sort="name", cursor=cursor)


async def test_다른_정렬의_커서는_VALIDATION_ERROR_다(db_session):
    for i in range(3):
        await _family(db_session, f"이름{i}", f"0101234{i:04d}", ["콩이"])
    recent = await _find(db_session, "", sort="recent", limit=1)
    with pytest.raises(CustomerInputError):
        await _find(db_session, "", sort="name", cursor=recent.next_cursor)


def _forged_cursor(key, customer_id) -> str:
    """정상 흐름으로는 만들 수 없는 값을 담은 커서 — 조작을 흉내 낸다."""
    raw = json.dumps(["name", key, customer_id]).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


@pytest.mark.parametrize("customer_id", [0, -1, 2**63])
async def test_customer_id가_bigint_범위를_벗어난_커서는_VALIDATION_ERROR_다(db_session, customer_id):
    with pytest.raises(CustomerInputError):
        await _find(db_session, "", sort="name", cursor=_forged_cursor("김민지", customer_id))


async def test_key에_NUL이_있는_커서는_VALIDATION_ERROR_다(db_session):
    with pytest.raises(CustomerInputError):
        await _find(db_session, "", sort="name", cursor=_forged_cursor("김민\x00지", 1))


async def _last_visit(session, customer_id):
    return (await session.execute(
        text("SELECT last_visit_at FROM customer_search_entries WHERE customer_id = :id"), {"id": customer_id}
    )).scalar_one()


async def test_마지막_방문_시각을_바꾸고_다시_만들어도_지킨다(db_session):
    """원본은 visits 라 검색 줄을 다시 만들 때(가족 수정) 이 칸은 건드리지 않는다."""
    from datetime import datetime, timezone

    customer_id = await _family(db_session, "김민지", "01012345678", ["콩이"])
    at = datetime(2026, 9, 23, 5, tzinfo=timezone.utc)
    search = CustomerSearchPgAdapter(db_session)
    await search.set_last_visit(A, customer_id, at)
    assert await _last_visit(db_session, customer_id) == at
    await search.rebuild_search_entry(A, customer_id)
    assert await _last_visit(db_session, customer_id) == at
    await search.set_last_visit(A, customer_id, None)
    assert await _last_visit(db_session, customer_id) is None


async def test_다른_매장_컨텍스트로는_마지막_방문_시각을_바꾸지_못한다(db_session):
    from datetime import datetime, timezone

    customer_id = await _family(db_session, "김민지", "01012345678", ["콩이"])
    await CustomerSearchPgAdapter(db_session).set_last_visit(
        B, customer_id, datetime(2026, 9, 23, tzinfo=timezone.utc))
    assert await _last_visit(db_session, customer_id) is None
