"""글에 닿는 쓰기가 다시 색인할 줄을 남기는지, 익명화가 검색 문서를 곧바로 지우는지 — 실제 배선으로 확인한다."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from customer.dependencies.customer_search_source_provider import get_customer_search_source_use_case
from hub.app.dtos.shop_context import system_context
from search.adapter.outbound.pg.search_document_pg_repository import SearchDocumentPgRepository
from search.tests.helpers.builders import NOW, doc
from tests.integration.support import bearer, error_of, make_operator, shop_with_owner
from visit.dependencies.visit_search_source_provider import get_visit_search_source_use_case

pytestmark = pytest.mark.integration

SEOUL = ZoneInfo("Asia/Seoul")
CUSTOMER = {"name": "김민지", "phone": "010-1234-5678", "marketing_consent": True, "memo": "전화보다 문자를 원하심"}
HEART = {"type_code": "heart_disease", "custom_label": None, "note": "약 복용 중"}
PATELLA = {"type_code": "patella_luxation", "custom_label": None, "note": None}


def _pet(name="콩이", memo=None, conditions=()):
    return {"name": name, "species": "dog", "breed": "말티즈", "sex": "female", "neutered": True, "birth_year": 2021,
            "weight_kg": 3.2, "no_known_conditions": not conditions, "conditions": list(conditions), "memo": memo}


def _at(days: int, hour: int) -> str:
    day = datetime.now(SEOUL).date() + timedelta(days=days)
    return datetime(day.year, day.month, day.day, hour, tzinfo=SEOUL).isoformat()


async def _shop(wired, name="Hiss Haus", owner="사장님", operator=None):
    operator = operator or await make_operator(wired)
    shop_id, login = await shop_with_owner(wired, operator, name, owner)
    return shop_id, bearer(login["access_token"]), operator


async def _family(wired, shop_id, headers, pet=None, phone="010-1234-5678"):
    response = await wired.api.post(f"/v1/shops/{shop_id}/customers", headers=headers,
                                    json={"customer": {**CUSTOMER, "phone": phone}, "pet": pet or _pet()})
    assert response.status_code == 201, response.text
    return response.json()["customer"]["customer_id"], response.json()["pets"][0]["pet_id"]


async def _jobs(wired) -> list[tuple]:
    """(shop_id, scope, ref_id, generation) — 넣은 순서."""
    async with wired.engine.connect() as conn:
        rows = await conn.execute(text("SELECT shop_id, scope, ref_id, generation FROM search_jobs ORDER BY id"))
        return [tuple(r) for r in rows]


async def _clear_jobs(wired) -> None:
    async with wired.engine.begin() as conn:
        await conn.execute(text("DELETE FROM search_jobs"))


async def _documents(wired, where="true") -> int:
    async with wired.engine.connect() as conn:
        return (await conn.execute(text(f"SELECT count(*) FROM search_documents WHERE {where}"))).scalar_one()


async def test_고객과_반려동물을_쓰면_다시_색인할_줄이_생긴다(wired):
    shop_id, headers, _ = await _shop(wired)
    customer_id, pet_id = await _family(wired, shop_id, headers)
    assert await _jobs(wired) == [(shop_id, "customer", customer_id, 1), (shop_id, "pet", pet_id, 1)]

    updated = await wired.api.put(f"/v1/shops/{shop_id}/pets/{pet_id}", headers=headers,
                                  json=_pet(memo="드라이를 무서워해요"))
    assert updated.status_code == 200, updated.text
    renamed = await wired.api.put(f"/v1/shops/{shop_id}/customers/{customer_id}", headers=headers,
                                  json={**CUSTOMER, "memo": "현관 앞에서 인계"})
    assert renamed.status_code == 200, renamed.text
    added = await wired.api.post(f"/v1/shops/{shop_id}/customers/{customer_id}/pets", headers=headers,
                                 json=_pet("두부"))
    assert added.status_code == 201, added.text
    second = added.json()["pet"]["pet_id"]
    assert await _jobs(wired) == [
        (shop_id, "customer", customer_id, 2), (shop_id, "pet", pet_id, 2), (shop_id, "pet", second, 1)]

    removed = await wired.api.delete(f"/v1/shops/{shop_id}/pets/{second}", headers=headers)
    assert removed.status_code == 204, removed.text
    assert (shop_id, "pet", second, 2) in await _jobs(wired)


async def test_방문과_기록을_쓰면_다시_색인할_줄이_생긴다(wired):
    shop_id, headers, _ = await _shop(wired)
    customer_id, pet_id = await _family(wired, shop_id, headers)
    await _clear_jobs(wired)

    booked = await wired.api.post(f"/v1/shops/{shop_id}/visits", headers=headers, json={
        "customer_id": customer_id, "pet_ids": [pet_id], "starts_at": _at(-1, 11), "memo": "발톱 짧게"})
    assert booked.status_code == 201, booked.text
    visit_id = booked.json()["visits"][0]["visit_id"]
    assert await _jobs(wired) == [(shop_id, "visit", visit_id, 1)]

    started = await wired.api.post(f"/v1/shops/{shop_id}/visits/transitions", headers=headers,
                                   json={"visit_ids": [visit_id], "action": "start"})
    assert started.status_code == 200, started.text
    assert await _jobs(wired) == [(shop_id, "visit", visit_id, 1)]        # 상태만 바뀐 것은 알리지 않는다

    saved = await wired.api.put(f"/v1/shops/{shop_id}/visits/{visit_id}/record", headers=headers,
                                json={"care_note": "얌전했어요", "internal_note": "귀를 만지면 싫어함"})
    assert saved.status_code == 200, saved.text
    assert await _jobs(wired) == [(shop_id, "visit", visit_id, 2)]

    deleted = await wired.api.delete(f"/v1/shops/{shop_id}/visits/{visit_id}/record", headers=headers)
    assert deleted.status_code == 204, deleted.text
    assert await _jobs(wired) == [(shop_id, "visit", visit_id, 3)]


async def test_거절된_쓰기는_줄을_남기지_않는다(wired):
    shop_id, headers, _ = await _shop(wired)
    customer_id, pet_id = await _family(wired, shop_id, headers)
    await _clear_jobs(wired)
    taken = await wired.api.post(f"/v1/shops/{shop_id}/customers", headers=headers,
                                 json={"customer": CUSTOMER, "pet": _pet()})
    assert taken.status_code == 409, taken.text
    missing = await wired.api.put(f"/v1/shops/{shop_id}/visits/999/record", headers=headers, json={})
    assert error_of(missing) == (404, "VISIT_NOT_FOUND")
    assert await _jobs(wired) == []


async def test_익명화하면_그_고객의_검색_문서가_같은_요청에서_사라진다(wired):
    shop_id, headers, operator = await _shop(wired)
    other_shop, _, _ = await _shop(wired, "B 매장", "B사장", operator)
    customer_id, pet_id = await _family(wired, shop_id, headers)
    stays_id, stays_pet = await _family(wired, shop_id, headers, _pet("두부"), phone="010-9999-8888")
    async with async_sessionmaker(wired.engine, expire_on_commit=False)() as session:
        documents = SearchDocumentPgRepository(session)
        mine, theirs = system_context(shop_id), system_context(other_shop)
        await documents.replace_target(mine, "visit", 7, [doc("care_note", 7, customer_id=customer_id, pet_id=pet_id),
                                                         doc("visit_memo", 7, customer_id=customer_id, pet_id=pet_id)], NOW)
        await documents.replace_target(mine, "pet", pet_id, [doc("pet_memo", pet_id, customer_id=customer_id, pet_id=pet_id)], NOW)
        await documents.replace_target(mine, "customer", customer_id, [doc("customer_memo", customer_id, customer_id=customer_id, pet_id=None)], NOW)
        await documents.replace_target(mine, "pet", stays_pet, [doc("pet_memo", stays_pet, customer_id=stays_id, pet_id=stays_pet)], NOW)
        await documents.replace_target(theirs, "customer", customer_id, [doc("customer_memo", customer_id, customer_id=customer_id, pet_id=None)], NOW)
        await session.commit()
    await _clear_jobs(wired)

    gone = await wired.api.delete(f"/v1/shops/{shop_id}/customers/{customer_id}", headers=headers)
    assert gone.status_code == 204, gone.text
    assert await _documents(wired, f"shop_id = {shop_id} AND customer_id = {customer_id}") == 0
    assert await _documents(wired, f"shop_id = {shop_id} AND customer_id = {stays_id}") == 1
    assert await _documents(wired, f"shop_id = {other_shop}") == 1
    assert await _jobs(wired) == [(shop_id, "customer", customer_id, 1)]


async def test_검색_원본은_실제_표에서_글을_읽고_익명화하면_비운다(wired):
    shop_id, headers, operator = await _shop(wired)
    other_shop, _, _ = await _shop(wired, "B 매장", "B사장", operator)
    customer_id, pet_id = await _family(wired, shop_id, headers, _pet(memo="드라이를 무서워해요", conditions=(HEART, PATELLA)))
    booked = await wired.api.post(f"/v1/shops/{shop_id}/visits", headers=headers, json={
        "customer_id": customer_id, "pet_ids": [pet_id], "starts_at": _at(-1, 11), "memo": "발톱 짧게"})
    visit_id = booked.json()["visits"][0]["visit_id"]
    await wired.api.post(f"/v1/shops/{shop_id}/visits/transitions", headers=headers,
                         json={"visit_ids": [visit_id], "action": "start"})
    saved = await wired.api.put(f"/v1/shops/{shop_id}/visits/{visit_id}/record", headers=headers,
                                json={"care_note": "얌전했어요", "internal_note": "귀를 만지면 싫어함"})
    assert saved.status_code == 200, saved.text
    mine, theirs = system_context(shop_id), system_context(other_shop)

    async def read(ctx, scope, ref_id):
        async with async_sessionmaker(wired.engine, expire_on_commit=False)() as session:
            source = get_visit_search_source_use_case(session) if scope == "visit" \
                else get_customer_search_source_use_case(session)
            return await source.documents(ctx, scope, ref_id)

    visit_docs = await read(mine, "visit", visit_id)
    assert [(d.kind, d.body) for d in visit_docs] == [
        ("care_note", "얌전했어요"), ("internal_note", "귀를 만지면 싫어함"), ("visit_memo", "발톱 짧게")]
    assert {d.happened_on for d in visit_docs} == {datetime.now(SEOUL).date() - timedelta(days=1)}
    pet_docs = await read(mine, "pet", pet_id)
    assert [(d.kind, d.body) for d in pet_docs] == [
        ("pet_memo", "드라이를 무서워해요"), ("condition_note", "슬개골 탈구"), ("condition_note", "심장 질환 — 약 복용 중")]
    condition_ids = [d.source_id for d in pet_docs if d.kind == "condition_note"]
    assert len(set(condition_ids)) == 2 and 0 not in condition_ids      # 지병 행의 실제 ID
    assert [d.body for d in await read(mine, "customer", customer_id)] == ["전화보다 문자를 원하심"]
    for scope, ref_id in (("visit", visit_id), ("pet", pet_id), ("customer", customer_id)):
        assert await read(theirs, scope, ref_id) == []

    done = await wired.api.post(f"/v1/shops/{shop_id}/visits/transitions", headers=headers,
                                json={"visit_ids": [visit_id], "action": "complete"})
    assert done.status_code == 200, done.text
    gone = await wired.api.delete(f"/v1/shops/{shop_id}/customers/{customer_id}", headers=headers)
    assert gone.status_code == 204, gone.text
    for scope, ref_id in (("visit", visit_id), ("pet", pet_id), ("customer", customer_id)):
        assert await read(mine, scope, ref_id) == []
