"""색인기를 실제 배선(허브 포트·PG·고객 행 잠금)으로 돌린다. 임베딩만 가짜다(정해진 벡터)."""
import asyncio
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

import scripts.reindex_search as reindex_search
from scripts.reindex_search import enqueue_all
from search.dependencies.indexer_provider import build_indexer
from search.domain.services.embedding_model import CURRENT_MODEL
from search.tests.helpers.fakes import FakeEmbedder
from tests.integration.support import bearer, make_operator, shop_with_owner

pytestmark = pytest.mark.integration

SEOUL = ZoneInfo("Asia/Seoul")
CUSTOMER = {"name": "김민지", "phone": "010-1234-5678", "marketing_consent": True, "memo": "전화보다 문자를 원하심"}
HEART = {"type_code": "heart_disease", "custom_label": None, "note": "약 복용 중"}


def _pet(name="콩이", memo="드라이를 무서워해요", conditions=(HEART,)):
    return {"name": name, "species": "dog", "breed": "말티즈", "sex": "female", "neutered": True, "birth_year": 2021,
            "weight_kg": 3.2, "no_known_conditions": not conditions, "conditions": list(conditions), "memo": memo}


def _at(days: int, hour: int) -> str:
    day = datetime.now(SEOUL).date() + timedelta(days=days)
    return datetime(day.year, day.month, day.day, hour, tzinfo=SEOUL).isoformat()


async def _shop(wired, name="Hiss Haus", owner="사장님", operator=None):
    operator = operator or await make_operator(wired)
    shop_id, login = await shop_with_owner(wired, operator, name, owner)
    return shop_id, bearer(login["access_token"]), operator


async def _family(wired, shop_id, headers, phone="010-1234-5678", pet=None):
    response = await wired.api.post(f"/v1/shops/{shop_id}/customers", headers=headers,
                                    json={"customer": {**CUSTOMER, "phone": phone}, "pet": pet or _pet()})
    assert response.status_code == 201, response.text
    return response.json()["customer"]["customer_id"], response.json()["pets"][0]["pet_id"]


async def _recorded_visit(wired, shop_id, headers, customer_id, pet_id, care="얌전했어요"):
    booked = await wired.api.post(f"/v1/shops/{shop_id}/visits", headers=headers, json={
        "customer_id": customer_id, "pet_ids": [pet_id], "starts_at": _at(-1, 11), "memo": "발톱 짧게"})
    assert booked.status_code == 201, booked.text
    visit_id = booked.json()["visits"][0]["visit_id"]
    for action in ("start", "complete"):
        moved = await wired.api.post(f"/v1/shops/{shop_id}/visits/transitions", headers=headers,
                                     json={"visit_ids": [visit_id], "action": action})
        assert moved.status_code == 200, moved.text
    saved = await wired.api.put(f"/v1/shops/{shop_id}/visits/{visit_id}/record", headers=headers,
                                json={"care_note": care, "internal_note": "귀를 만지면 싫어함"})
    assert saved.status_code == 200, saved.text
    return visit_id


async def _index(wired, embedder=None, later=timedelta(0)):
    """색인기를 한 번 돌린다. later 만큼 뒤의 시각으로 — 미룬 줄을 집게 할 때 쓴다."""
    embedder = embedder if embedder is not None else FakeEmbedder()
    async with async_sessionmaker(wired.engine, expire_on_commit=False, autoflush=False)() as session:
        report = await build_indexer(
            session, embedder=embedder, now=lambda: datetime.now(timezone.utc) + later).run_once()
    return report, embedder


async def _rows(wired, sql, **params):
    async with wired.engine.connect() as conn:
        return [tuple(r) for r in await conn.execute(text(sql), params)]


async def _documents(wired, shop_id):
    return await _rows(wired, "SELECT kind, body, embedding IS NOT NULL, model FROM search_documents "
                              "WHERE shop_id = :shop ORDER BY kind, body", shop=shop_id)


async def test_적은_글이_색인기를_지나_검색_문서가_된다(wired):
    shop_id, headers, _ = await _shop(wired)
    customer_id, pet_id = await _family(wired, shop_id, headers)
    visit_id = await _recorded_visit(wired, shop_id, headers, customer_id, pet_id)

    report, embedder = await _index(wired)
    assert (report.claimed, report.indexed, report.deferred) == (3, 3, 0)
    assert await _documents(wired, shop_id) == [
        ("care_note", "얌전했어요", True, CURRENT_MODEL),
        ("condition_note", "심장 질환 — 약 복용 중", True, CURRENT_MODEL),
        ("customer_memo", "전화보다 문자를 원하심", True, CURRENT_MODEL),
        ("internal_note", "귀를 만지면 싫어함", True, CURRENT_MODEL),
        ("pet_memo", "드라이를 무서워해요", True, CURRENT_MODEL),
        ("visit_memo", "발톱 짧게", True, CURRENT_MODEL),
    ]
    meta = await _rows(wired, "SELECT kind, customer_id, pet_id, visit_id, happened_on FROM search_documents "
                              "WHERE kind IN ('care_note', 'pet_memo', 'customer_memo') ORDER BY kind")
    yesterday = datetime.now(SEOUL).date() - timedelta(days=1)
    assert meta == [("care_note", customer_id, pet_id, visit_id, yesterday),
                    ("customer_memo", customer_id, None, None, None), ("pet_memo", customer_id, pet_id, None, None)]
    assert await _rows(wired, "SELECT count(*) FROM search_jobs") == [(0,)]
    assert {kind for kind, _ in embedder.calls} == {"passage"}


async def test_고치면_바뀐_글만_다시_임베딩하고_지우면_문서가_사라진다(wired):
    shop_id, headers, _ = await _shop(wired)
    customer_id, pet_id = await _family(wired, shop_id, headers)
    visit_id = await _recorded_visit(wired, shop_id, headers, customer_id, pet_id)
    await _index(wired)

    saved = await wired.api.put(f"/v1/shops/{shop_id}/visits/{visit_id}/record", headers=headers, json={
        "version": 1, "care_note": "드라이할 때 짖었어요", "internal_note": "귀를 만지면 싫어함"})
    assert saved.status_code == 200, saved.text
    _, embedder = await _index(wired)
    assert embedder.calls == [("passage", ["드라이할 때 짖었어요"])]

    cleared = await wired.api.put(f"/v1/shops/{shop_id}/pets/{pet_id}", headers=headers, json=_pet(memo=None, conditions=()))
    assert cleared.status_code == 200, cleared.text
    await _index(wired)
    kinds = [kind for kind, *_ in await _documents(wired, shop_id)]
    assert kinds == ["care_note", "customer_memo", "internal_note", "visit_memo"]


async def test_임베딩이_죽어_있으면_글만_들어가고_살아나면_벡터가_채워진다(wired):
    shop_id, headers, _ = await _shop(wired)
    await _family(wired, shop_id, headers, pet=_pet(conditions=()))
    down = FakeEmbedder()
    down.down = True
    report, _ = await _index(wired, down)
    assert (report.indexed, report.deferred) == (0, 2)
    assert await _documents(wired, shop_id) == [
        ("customer_memo", "전화보다 문자를 원하심", False, None), ("pet_memo", "드라이를 무서워해요", False, None)]
    assert (await _index(wired))[0].claimed == 0                       # 미룬 줄은 아직 때가 아니다
    report, _ = await _index(wired, later=timedelta(seconds=31))
    assert (report.claimed, report.indexed) == (2, 2)
    assert [row[2:] for row in await _documents(wired, shop_id)] == [(True, CURRENT_MODEL)] * 2


async def test_익명화하면_곧바로_사라지고_색인기가_돌아도_되살아나지_않는다(wired):
    shop_id, headers, _ = await _shop(wired)
    customer_id, pet_id = await _family(wired, shop_id, headers)
    await _recorded_visit(wired, shop_id, headers, customer_id, pet_id)
    await _index(wired)
    gone = await wired.api.delete(f"/v1/shops/{shop_id}/customers/{customer_id}", headers=headers)
    assert gone.status_code == 204, gone.text
    assert await _documents(wired, shop_id) == []
    await _index(wired)
    await enqueue_all_committed(wired)
    await _index(wired)
    assert await _documents(wired, shop_id) == []
    assert await _rows(wired, "SELECT count(*) FROM search_jobs") == [(0,)]


async def enqueue_all_committed(wired, **kwargs):
    async with async_sessionmaker(wired.engine, expire_on_commit=False)() as session:
        counts = await enqueue_all(session, **kwargs)
        await session.commit()
    return counts


async def test_다른_매장의_글은_섞이지_않는다(wired):
    a_shop, a, operator = await _shop(wired, "A 매장", "A사장")
    b_shop, b, _ = await _shop(wired, "B 매장", "B사장", operator)
    await _family(wired, a_shop, a, pet=_pet(memo="A 매장의 글", conditions=()))
    await _family(wired, b_shop, b, pet=_pet(memo="B 매장의 글", conditions=()))
    await _index(wired)
    assert [row[1] for row in await _documents(wired, a_shop) if row[0] == "pet_memo"] == ["A 매장의 글"]
    assert [row[1] for row in await _documents(wired, b_shop) if row[0] == "pet_memo"] == ["B 매장의 글"]


async def test_색인기는_고객_행을_잠근_뒤에_쓴다(wired):
    """익명화·수정이 고객 행을 쥐고 있으면 색인기의 쓰기는 그 뒤로 밀린다(잠금 순서: 고객 행 → 검색 표)."""
    shop_id, headers, _ = await _shop(wired)
    customer_id, _ = await _family(wired, shop_id, headers, pet=_pet(conditions=()))
    factory = async_sessionmaker(wired.engine, expire_on_commit=False, autoflush=False)
    async with factory() as holder:
        await holder.execute(text("SELECT id FROM customers WHERE id = :id FOR UPDATE"), {"id": customer_id})
        indexing = asyncio.create_task(_index(wired))
        await asyncio.sleep(0.5)
        assert not indexing.done()
        assert await _documents(wired, shop_id) == []
        await holder.commit()
    report, _ = await asyncio.wait_for(indexing, timeout=5)
    assert report.indexed == 2 and len(await _documents(wired, shop_id)) == 2


async def test_맞춤_스크립트는_원본을_줄에_넣고_주인_없는_문서를_지우게_한다(wired):
    a_shop, a, operator = await _shop(wired, "A 매장", "A사장")
    b_shop, b, _ = await _shop(wired, "B 매장", "B사장", operator)
    a_customer, a_pet = await _family(wired, a_shop, a)
    a_visit = await _recorded_visit(wired, a_shop, a, a_customer, a_pet)
    b_customer, b_pet = await _family(wired, b_shop, b)
    await _index(wired)
    async with wired.engine.begin() as conn:      # 어긋난 상태 — 문서 하나가 사라지고, 원본 없는 문서가 남았다
        await conn.execute(text("DELETE FROM search_documents WHERE kind = 'pet_memo' AND shop_id = :s"), {"s": a_shop})
        await conn.execute(text(
            "INSERT INTO search_documents (shop_id, kind, source_id, customer_id, pet_id, visit_id, body, updated_at) "
            "VALUES (:s, 'care_note', 999, :c, :p, 999, '원본이 없는 글', now()), "
            "       (:s, 'condition_note', 998, :c, 997, NULL, '원본이 없는 지병', now())"),
            {"s": a_shop, "c": a_customer, "p": a_pet})

    counts = await enqueue_all_committed(wired, shop_id=a_shop)
    assert counts == {"visit": 1, "pet": 1, "customer": 1}
    assert {row[0] for row in await _rows(wired, "SELECT shop_id FROM search_jobs")} == {a_shop}
    await _index(wired)
    bodies = {row[1] for row in await _documents(wired, a_shop)}
    assert "드라이를 무서워해요" in bodies and "원본이 없는 글" in bodies       # 고쳤지만 주인 없는 것은 그대로

    counts = await enqueue_all_committed(wired, purge_orphans=True)
    # 두 매장의 원본(방문 1·아이 2·고객 2) + 문서가 가리키는 대상(방문 2 — 999 포함, 아이 3 — 997 포함, 고객 2)
    assert counts == {"visit": 3, "pet": 5, "customer": 4}
    await _index(wired)
    bodies = {row[1] for row in await _documents(wired, a_shop)}
    assert "원본이 없는 글" not in bodies and "원본이 없는 지병" not in bodies
    assert len(bodies) == 6 and len(await _documents(wired, b_shop)) == 3
    assert a_visit and b_customer and b_pet


async def test_맞춤_스크립트의_엔진도_hide_parameters를_켠다(migrated_test_db, monkeypatch):
    captured = {}
    original_create = reindex_search.create_async_engine

    def _spy(url, **kwargs):
        captured.update(kwargs)
        return original_create(url, **kwargs)

    monkeypatch.setattr(reindex_search, "create_async_engine", _spy)
    monkeypatch.setattr(reindex_search, "DATABASE_URL", migrated_test_db)
    await reindex_search._run(None, False)
    assert captured.get("hide_parameters") is True
