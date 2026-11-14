"""search 의 표와 저장소 — 실제 PG(pgvector·pg_trgm)로 확인한다."""
from __future__ import annotations

import asyncio
from datetime import date, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker

from core.observer.in_process_event_bus import InProcessEventBus
from hub.app.dtos.search_events import SEARCH_SCOPES, SearchSourceChanged
from search.adapter.inbound.observer.source_changed_subscriber import handle_source_changed
from search.adapter.outbound.pg.search_candidate_pg_repository import SearchCandidatePgRepository
from search.adapter.outbound.pg.search_document_pg_repository import SearchDocumentPgRepository
from search.adapter.outbound.pg.search_job_pg_repository import SearchJobPgRepository
from search.app.use_cases.forget_customer_interactor import ForgetCustomerInteractor
from search.domain.entities.search_document import KINDS, SCOPES, PetScope
from search.domain.services.embedding_model import CURRENT_MODEL as MODEL_NOW
from search.domain.services.retry import CLAIM_HOLD
from search.tests.helpers.builders import NOW, ctx, doc

pytestmark = pytest.mark.integration

VECTOR = tuple([1.0] + [0.0] * 383)
MODEL = "test-model"


async def _count(session, table: str, where: str = "true") -> int:
    return (await session.execute(text(f"SELECT count(*) FROM {table} WHERE {where}"))).scalar_one()


# --- 스키마 -------------------------------------------------------------------------------------------------------

async def test_확장과_색인이_있다(db_session):
    extensions = set((await db_session.execute(text("SELECT extname FROM pg_extension"))).scalars())
    assert {"vector", "pg_trgm"} <= extensions
    indexes = dict((await db_session.execute(text(
        "SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'search_documents'"))).all())
    assert "gin" in indexes["ix_search_documents_body_trgm"] and "gin_trgm_ops" in indexes["ix_search_documents_body_trgm"]
    assert "hnsw" in indexes["ix_search_documents_embedding_hnsw"]
    assert "vector_cosine_ops" in indexes["ix_search_documents_embedding_hnsw"]


async def test_종류와_대상의_목록은_도메인과_같다(db_session):
    checks = dict((await db_session.execute(text(
        "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint WHERE conname IN "
        "('ck_search_documents_kind', 'ck_search_jobs_scope')"))).all())
    for kind in KINDS:
        assert f"'{kind}'" in checks["ck_search_documents_kind"]
    assert checks["ck_search_documents_kind"].count("'") == 2 * len(KINDS)
    for scope in SCOPES:
        assert f"'{scope}'" in checks["ck_search_jobs_scope"]
    assert SCOPES == SEARCH_SCOPES


async def test_벡터와_모델_이름은_함께_있거나_함께_없다(db_session):
    documents = SearchDocumentPgRepository(db_session)
    with pytest.raises(IntegrityError):
        await documents.replace_target(ctx(), "visit", 7, [doc("care_note", 7, embedding=VECTOR, model=None)], NOW)


# --- 문서 저장소 --------------------------------------------------------------------------------------------------

async def test_대상의_문서를_넣고_덮고_없어진_것은_지운다(db_session):
    documents = SearchDocumentPgRepository(db_session)
    await documents.replace_target(ctx(), "visit", 7, [
        doc("care_note", 7, body="얌전했어요", embedding=VECTOR, model=MODEL), doc("visit_memo", 7, body="발톱 짧게"),
    ], NOW)
    await documents.replace_target(ctx(), "visit", 8, [doc("care_note", 8, body="다른 방문")], NOW)
    await documents.replace_target(ctx(), "visit", 7, [doc("care_note", 7, body="드라이를 무서워해요")], NOW)

    [kept] = await documents.list_for_target(ctx(), "visit", 7)
    assert (kept.kind, kept.body, kept.embedding, kept.model) == ("care_note", "드라이를 무서워해요", None, None)
    assert [d.body for d in await documents.list_for_target(ctx(), "visit", 8)] == ["다른 방문"]
    assert await _count(db_session, "search_documents") == 2


async def test_벡터를_넣고_그대로_읽는다(db_session):
    documents = SearchDocumentPgRepository(db_session)
    await documents.replace_target(ctx(), "pet", 101, [
        doc("pet_memo", 101, embedding=VECTOR, model=MODEL, happened_on=None),
        doc("condition_note", 55, pet_id=101, body="심장 질환 — 약 복용 중"),
    ], NOW)
    found = {d.kind: d for d in await documents.list_for_target(ctx(), "pet", 101)}
    assert found["pet_memo"].embedding == VECTOR and found["pet_memo"].model == MODEL
    assert found["condition_note"].embedding is None and found["condition_note"].source_id == 55


async def test_빈_목록으로_맞추면_그_대상의_문서만_사라진다(db_session):
    documents = SearchDocumentPgRepository(db_session)
    await documents.replace_target(ctx(), "pet", 101, [
        doc("pet_memo", 101), doc("condition_note", 55, pet_id=101), doc("condition_note", 56, pet_id=101),
    ], NOW)
    await documents.replace_target(ctx(), "pet", 102, [doc("condition_note", 57, pet_id=102)], NOW)
    await documents.replace_target(ctx(), "pet", 101, [], NOW)
    assert await documents.list_for_target(ctx(), "pet", 101) == []
    assert len(await documents.list_for_target(ctx(), "pet", 102)) == 1


async def test_다른_매장의_같은_대상은_읽히지도_지워지지도_않는다(db_session):
    documents = SearchDocumentPgRepository(db_session)
    await documents.replace_target(ctx(1), "visit", 7, [doc("care_note", 7, body="우리 매장")], NOW)
    await documents.replace_target(ctx(2), "visit", 7, [doc("care_note", 7, body="다른 매장")], NOW)
    assert [d.body for d in await documents.list_for_target(ctx(1), "visit", 7)] == ["우리 매장"]
    await documents.replace_target(ctx(1), "visit", 7, [], NOW)
    await documents.delete_for_customer(ctx(1), 1)
    assert [d.body for d in await documents.list_for_target(ctx(2), "visit", 7)] == ["다른 매장"]


async def test_그_대상의_것이_아닌_문서는_쓰지_않는다(db_session):
    documents = SearchDocumentPgRepository(db_session)
    with pytest.raises(ValueError):
        await documents.replace_target(ctx(), "visit", 7, [doc("care_note", 7), doc("care_note", 8)], NOW)
    assert await _count(db_session, "search_documents") == 0


# --- 줄 -----------------------------------------------------------------------------------------------------------

async def test_같은_대상을_거듭_넣어도_한_줄이고_세대가_오른다(db_session):
    queue = SearchJobPgRepository(db_session)
    for _ in range(3):
        await queue.enqueue(ctx(), "visit", 7, NOW)
    await queue.enqueue(ctx(2), "visit", 7, NOW)
    rows = (await db_session.execute(text("SELECT shop_id, generation FROM search_jobs ORDER BY shop_id"))).all()
    assert [tuple(r) for r in rows] == [(1, 3), (2, 1)]


async def test_집은_줄은_뒤로_밀리고_시각이_안_된_줄은_집지_않는다(db_session):
    queue = SearchJobPgRepository(db_session)
    await queue.enqueue(ctx(), "visit", 7, NOW)
    await queue.enqueue(ctx(), "pet", 101, NOW + timedelta(seconds=30))
    [job] = await queue.claim_due(NOW, 20)
    assert (job.scope, job.ref_id, job.generation, job.attempts) == ("visit", 7, 1, 0)
    assert await queue.claim_due(NOW + timedelta(seconds=1), 20) == []            # 집은 줄은 60초 뒤로
    assert len(await queue.claim_due(NOW + CLAIM_HOLD, 20)) == 2


async def test_끝내기는_세대가_그대로일_때만_지운다(db_session):
    queue = SearchJobPgRepository(db_session)
    await queue.enqueue(ctx(), "visit", 7, NOW)
    await queue.enqueue(ctx(), "visit", 8, NOW)
    seven, eight = await queue.claim_due(NOW, 20)
    await queue.enqueue(ctx(), "visit", 7, NOW)          # 처리하는 사이에 다시 바뀌었다
    await queue.finish(seven)
    await queue.finish(eight)
    rows = (await db_session.execute(text("SELECT ref_id, generation, next_attempt_at FROM search_jobs"))).all()
    assert [(r.ref_id, r.generation) for r in rows] == [(7, 2)]
    assert rows[0].next_attempt_at == NOW                # 지금으로 당겨져 있다 — 곧 다시 집힌다


async def test_미루기는_간격을_늘리고_세대가_올랐으면_건드리지_않는다(db_session):
    queue = SearchJobPgRepository(db_session)
    await queue.enqueue(ctx(), "visit", 7, NOW)
    [job] = await queue.claim_due(NOW, 20)
    await queue.retry_later(job, NOW)
    [again] = await queue.claim_due(NOW + timedelta(seconds=30), 20)
    assert again.attempts == 1
    await queue.retry_later(again, NOW)
    row = (await db_session.execute(text("SELECT attempts, next_attempt_at FROM search_jobs"))).one()
    assert (row.attempts, row.next_attempt_at) == (2, NOW + timedelta(seconds=60))

    await queue.enqueue(ctx(), "visit", 7, NOW)
    await queue.retry_later(again, NOW + timedelta(hours=1))
    row = (await db_session.execute(text("SELECT attempts, generation, next_attempt_at FROM search_jobs"))).one()
    assert (row.attempts, row.generation, row.next_attempt_at) == (0, 2, NOW)


async def test_두_색인기는_같은_줄을_겹쳐_집지_않는다(db_engine):
    factory = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)
    async with factory() as seed:
        queue = SearchJobPgRepository(seed)
        for ref in range(1, 7):
            await queue.enqueue(ctx(), "visit", ref, NOW)
        await seed.commit()
    async with factory() as first, factory() as second:
        mine = await SearchJobPgRepository(first).claim_due(NOW, 4)            # 잠금을 쥔 채
        theirs = await asyncio.wait_for(SearchJobPgRepository(second).claim_due(NOW, 4), timeout=5)
        await first.commit()
        await second.commit()
    assert len(mine) == 4 and len(theirs) == 2
    assert {j.ref_id for j in mine}.isdisjoint({j.ref_id for j in theirs})


# --- 구독자와 잊기 ------------------------------------------------------------------------------------------------

async def test_이벤트를_내면_같은_트랜잭션에_줄이_생기고_롤백하면_없다(db_session):
    bus = InProcessEventBus(db_session, [(handle_source_changed, SearchSourceChanged)])
    await bus.publish(SearchSourceChanged(ctx=ctx(3), scope="pet", ref_id=101))
    await bus.publish(SearchSourceChanged(ctx=ctx(3), scope="pet", ref_id=101))
    assert await _count(db_session, "search_jobs", "shop_id = 3 AND scope = 'pet' AND ref_id = 101") == 1
    await db_session.rollback()
    assert await _count(db_session, "search_jobs") == 0


async def test_잊기는_부른_쪽의_트랜잭션_안에서_지우고_롤백하면_남는다(db_session):
    documents, queue = SearchDocumentPgRepository(db_session), SearchJobPgRepository(db_session)
    await documents.replace_target(ctx(), "visit", 7, [doc("care_note", 7), doc("internal_note", 7)], NOW)
    await documents.replace_target(ctx(), "pet", 101, [doc("pet_memo", 101), doc("condition_note", 5, pet_id=101)], NOW)
    await documents.replace_target(ctx(), "customer", 1, [doc("customer_memo", 1, pet_id=None)], NOW)
    await documents.replace_target(ctx(), "visit", 9, [doc("care_note", 9, customer_id=2, pet_id=201)], NOW)
    await db_session.commit()

    forget = ForgetCustomerInteractor(documents=documents, queue=queue, now=lambda: NOW)
    await forget.forget_customer(ctx(), 1)
    assert await _count(db_session, "search_documents", "customer_id = 1") == 0
    assert await _count(db_session, "search_documents", "customer_id = 2") == 1
    assert await _count(db_session, "search_jobs", "scope = 'customer' AND ref_id = 1") == 1
    await db_session.rollback()
    assert await _count(db_session, "search_documents", "customer_id = 1") == 5
    assert await _count(db_session, "search_jobs") == 0


# --- 후보 질의 ----------------------------------------------------------------------------------------------------

def _away(similarity: float) -> tuple[float, ...]:
    """VECTOR(0번 축)와 cosine 유사도가 similarity 인 길이 1 의 벡터."""
    import math

    return (similarity, math.sqrt(1 - similarity ** 2)) + (0.0,) * 382


async def _seed_two_shops(session):
    documents = SearchDocumentPgRepository(session)
    for shop_id, label in ((1, "우리 매장"), (2, "다른 매장")):
        await documents.replace_target(ctx(shop_id), "pet", 101, [
            doc("pet_memo", 101, body=f"입질이 있어요 — {label}", embedding=VECTOR, model=MODEL_NOW)], NOW)
    return documents


async def test_글자_후보는_이_매장의_문서만이다(db_session):
    """S1 — 결과에 이름을 붙이는 단계가 걸러 주기 전에, 질의 자체가 매장으로 거른다."""
    await _seed_two_shops(db_session)
    candidates = SearchCandidatePgRepository(db_session)
    assert [c.body for c in await candidates.lexical(ctx(1), "입질", "%입질%", None)] == ["입질이 있어요 — 우리 매장"]
    assert [c.body for c in await candidates.lexical(ctx(2), "입질", "%입질%", None)] == ["입질이 있어요 — 다른 매장"]
    assert await candidates.lexical(ctx(3), "입질", "%입질%", None) == []


async def test_뜻_후보는_이_매장의_문서만이다(db_session):
    await _seed_two_shops(db_session)
    candidates = SearchCandidatePgRepository(db_session)
    assert [c.body for c in await candidates.semantic(ctx(1), VECTOR, None)] == ["입질이 있어요 — 우리 매장"]
    assert [c.body for c in await candidates.semantic(ctx(2), VECTOR, None)] == ["입질이 있어요 — 다른 매장"]
    assert await candidates.semantic(ctx(3), VECTOR, None) == []


async def test_아이로_좁힌_후보도_이_매장_안에서만이다(db_session):
    await _seed_two_shops(db_session)
    candidates = SearchCandidatePgRepository(db_session)
    scope = PetScope(pet_id=101, customer_id=1)
    assert [c.body for c in await candidates.lexical(ctx(1), "입질", "%입질%", scope)] == ["입질이 있어요 — 우리 매장"]
    assert [c.body for c in await candidates.semantic(ctx(1), VECTOR, scope)] == ["입질이 있어요 — 우리 매장"]
    assert await candidates.lexical(ctx(1), "입질", "%입질%", PetScope(pet_id=999, customer_id=999)) == []


async def test_뜻_후보는_가장_가까운_것에서_여유_안쪽만이고_벡터_없는_문서와_다른_모델은_빠진다(db_session):
    """이 모델은 관계없는 글도 0.8 안팎이 나온다 — 바닥(0.80)만으로는 못 거른다. 1등에서 0.04 안쪽만 남긴다."""
    documents, candidates = SearchDocumentPgRepository(db_session), SearchCandidatePgRepository(db_session)
    for visit_id, body, embedding, model in (
        (1, "여유 끝", _away(0.931), MODEL_NOW), (2, "가장 가까움", _away(0.97), MODEL_NOW),
        (3, "여유 밖", _away(0.92), MODEL_NOW), (4, "벡터 없음", None, None),
        (5, "다른 모델", VECTOR, "old-model"), (6, "바로 다음", _away(0.96), MODEL_NOW),
    ):
        await documents.replace_target(ctx(), "visit", visit_id, [
            doc("care_note", visit_id, body=body, embedding=embedding, model=model)], NOW)
    assert [c.body for c in await candidates.semantic(ctx(), VECTOR, None)] == ["가장 가까움", "바로 다음", "여유 끝"]
    assert [c.body for c in await candidates.semantic(ctx(), VECTOR, None, limit=1)] == ["가장 가까움"]


async def test_뜻_후보는_바닥_아래면_가장_가까워도_빠지고_열_개까지다(db_session):
    documents, candidates = SearchDocumentPgRepository(db_session), SearchCandidatePgRepository(db_session)
    await documents.replace_target(ctx(), "visit", 1, [
        doc("care_note", 1, body="바닥 아래", embedding=_away(0.79), model=MODEL_NOW)], NOW)
    assert await candidates.semantic(ctx(), VECTOR, None) == []
    for visit_id in range(2, 15):
        await documents.replace_target(ctx(), "visit", visit_id, [
            doc("care_note", visit_id, body=f"가까움 {visit_id}", embedding=_away(0.9), model=MODEL_NOW)], NOW)
    assert len(await candidates.semantic(ctx(), VECTOR, None)) == 10


async def test_글자_후보는_그대로_든_글이_먼저이고_닮은_글이_뒤따른다(db_session):
    documents, candidates = SearchDocumentPgRepository(db_session), SearchCandidatePgRepository(db_session)
    for visit_id, body in ((1, "슬개골 탈구 수술을 했어요"), (2, "슬개골탈구 주의"), (3, "가위컷으로 정리했어요")):
        await documents.replace_target(ctx(), "visit", visit_id, [doc("care_note", visit_id, body=body)], NOW)
    found = [c.body for c in await candidates.lexical(ctx(), "슬개골탈구", "%슬개골탈구%", None)]
    assert found[0] == "슬개골탈구 주의"                      # 그대로 든 글
    assert "가위컷으로 정리했어요" not in found
    assert len(await candidates.lexical(ctx(), "슬개골탈구", "%슬개골탈구%", None, limit=1)) == 1
