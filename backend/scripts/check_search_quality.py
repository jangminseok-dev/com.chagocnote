"""기록 검색의 품질 확인 — 지어낸 미용 기록 60개에서 질문 30개의 정답이 위 5개 안에 드는 수를 잰다(⑨ 설계 3.9).

기준: 30개 가운데 24개 이상(0.8). 그리고 맞는 글이 여럿인 질문 8개의 정답 18개 가운데 12개 이상이 결과에 든다
(말을 바꿔 물었을 때 흩어진 글을 얼마나 모으는가). 하나라도 못 미치면 종료 코드 1.
실제 임베딩 프로세스(compose 의 embed)와 실제 PG(개발 DB)로 돈다 — 그래서 CI 에는 넣지 않았다(로컬 확인).
검색 유스케이스와 같은 부품(임베딩 어댑터·후보 질의·순위 합치기)을 쓴다. 이름·사진 붙이기만 뺐다(가짜 매장이라 고객이 없다).
확인용 매장 번호(QUALITY_SHOP_ID)의 검색 문서만 넣고, 끝나면 지운다. 다른 매장의 것은 건드리지 않는다.
틀린 질문은 번호만 찍는다.
사용: cd infra && docker compose run --rm backend python scripts/check_search_quality.py [--verbose]
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import date, datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.config import DATABASE_URL
from hub.app.dtos.shop_context import system_context
from scripts.search_quality_set import DOCUMENTS, LEXICAL, MULTI, PARAPHRASED
from search.adapter.outbound.pg.search_candidate_pg_repository import SearchCandidatePgRepository
from search.adapter.outbound.pg.search_document_pg_repository import SearchDocumentPgRepository
from search.app.ports.output.embedding_port import INDEX_TIMEOUT, QUERY_TIMEOUT, EmbeddingPort
from search.dependencies.search_wiring import get_embedder
from search.domain.entities.search_document import SearchDocument
from search.domain.services.embedding_model import CURRENT_MODEL
from search.domain.services.rank_fusion import collapse_visits, fuse
from search.domain.services.search_query import clean_query, like_pattern

QUALITY_SHOP_ID = 9_000_000_001   # 실제 매장과 겹치지 않는 번호 — 검색 표에는 매장으로 가는 외래 키가 없다
TOP = 5
PASS_MARK = 24
# 맞는 글이 여럿인 질문 — 결과(최대 30줄) 안에 든 정답의 수. 18개 가운데 12개 이상.
RECALL_MARK = 12


async def _clear(session: AsyncSession) -> None:
    await session.execute(text("DELETE FROM search_documents WHERE shop_id = :shop"), {"shop": QUALITY_SHOP_ID})
    await session.commit()


async def _seed(session: AsyncSession, embedder: EmbeddingPort) -> None:
    embedded = await embedder.embed("passage", list(DOCUMENTS), INDEX_TIMEOUT * 6)
    if embedded is None:
        raise SystemExit("임베딩 프로세스가 응답하지 않습니다. `docker compose up -d embed` 뒤에 다시 돌려 주세요.")
    ctx, now = system_context(QUALITY_SHOP_ID), datetime.now(timezone.utc)
    repository = SearchDocumentPgRepository(session)
    for number, (body, vector) in enumerate(zip(DOCUMENTS, embedded.vectors), start=1):
        # 글마다 다른 방문의 케어 노트로 넣는다 — 같은 방문 접기에 걸리지 않게.
        await repository.replace_target(ctx, "visit", number, [SearchDocument(
            kind="care_note", source_id=number, customer_id=1, pet_id=1, visit_id=number,
            happened_on=date(2026, 11, 1), body=body, embedding=vector, model=CURRENT_MODEL)], now)
    await session.commit()


async def _top(session: AsyncSession, embedder: EmbeddingPort, question: str) -> tuple[list[int], bool]:
    """검색 유스케이스와 같은 차례 — 다듬기 → 임베딩 → 글자 후보·뜻 후보 → 합치기 → 접기. 가까운 순의 글 번호."""
    ctx, q = system_context(QUALITY_SHOP_ID), clean_query(question)
    candidates = SearchCandidatePgRepository(session)
    embedded = await embedder.embed("query", [q], QUERY_TIMEOUT * 4)
    lexical = await candidates.lexical(ctx, q, like_pattern(q), None)
    semantic = await candidates.semantic(ctx, embedded.vectors[0], None) if embedded is not None else []
    found = {c.id: c for c in (*lexical, *semantic)}
    ranked = collapse_visits([found[i] for i in fuse([c.id for c in lexical], [c.id for c in semantic])])
    return [c.source_id for c in ranked], embedded is not None


async def measure(session: AsyncSession, embedder: EmbeddingPort, verbose: bool = False) -> dict[str, int]:
    """글을 넣고 질문을 돌려 {"lexical": 맞힌 수, "paraphrased": 맞힌 수} 를 돌려준다. 끝나면 넣은 글을 지운다."""
    await _clear(session)
    try:
        await _seed(session, embedder)
        hits = {"lexical": 0, "paraphrased": 0}
        for name, questions in (("lexical", LEXICAL), ("paraphrased", PARAPHRASED)):
            missed = []
            for number, (question, answer) in enumerate(questions, start=1):
                ranked, semantic = await _top(session, embedder, question)
                top = ranked[:TOP]
                if not semantic:
                    raise SystemExit("질문을 임베딩하지 못했습니다. 임베딩 프로세스를 확인해 주세요.")
                if answer in top:
                    hits[name] += 1
                else:
                    missed.append(number)
                if verbose:   # 번호와 순위만 — 글은 찍지 않는다
                    place = top.index(answer) + 1 if answer in top else "-"
                    print(f"  {name} {number:>2}: 정답 {answer:>2} 순위 {place}  위 {TOP}: {top}")
            print(f"{name}: {hits[name]}/{len(questions)}" + (f"  (틀린 질문 번호: {missed})" if missed else ""))
        hits["multi"] = 0
        for question, answers in MULTI:
            ranked, _ = await _top(session, embedder, question)
            hits["multi"] += len(set(answers) & set(ranked))
        print(f"multi(맞는 글이 여럿): {hits['multi']}/{sum(len(a) for _, a in MULTI)}  (기준 {RECALL_MARK})")
        return hits
    finally:
        await session.rollback()
        await _clear(session)


async def _run(verbose: bool) -> dict[str, int]:
    engine = create_async_engine(DATABASE_URL, hide_parameters=True)
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            return await measure(session, get_embedder(), verbose)
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="기록 검색의 품질 확인")
    parser.add_argument("--verbose", action="store_true", help="질문마다 정답의 순위를 찍는다(글은 찍지 않는다)")
    hits = asyncio.run(_run(parser.parse_args().verbose))
    total, asked = hits["lexical"] + hits["paraphrased"], len(LEXICAL) + len(PARAPHRASED)
    print(f"합계: {total}/{asked}  (기준 {PASS_MARK})")
    sys.exit(0 if total >= PASS_MARK and hits["multi"] >= RECALL_MARK else 1)


if __name__ == "__main__":
    main()
