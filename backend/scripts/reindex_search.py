"""기록 검색의 문서를 원본에 다시 맞춘다 — 다시 색인할 줄(search_jobs)에 대상을 넣는다. 실제로 맞추는 것은 색인기다.

    모든 방문·반려동물·고객(살아 있는)을 줄에 넣는다. 처음 채울 때, 임베딩 모델을 바꿨을 때, 어긋났을 때 쓴다.
    --shop <id>       그 매장만
    --purge-orphans   지금 있는 검색 문서의 대상도 줄에 넣는다 — 원본이 사라진 문서를 색인기가 지운다.

여러 번 돌려도 결과가 같다(같은 대상은 한 줄이다). 글을 읽지도 찍지도 않는다 — ID 와 건수만 다룬다.
색인기는 API 프로세스(backend) 안에서 돈다. 줄이 다 빠졌는지는 `SELECT count(*) FROM search_jobs` 로 본다.
사용: cd infra && docker compose run --rm backend python scripts/reindex_search.py [--shop <id>] [--purge-orphans]
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.config import DATABASE_URL

# 원본 표에서 대상의 (매장, ID) 를 고르는 질의 — 익명화한 고객과 그 아이는 넣지 않는다(문서가 없다).
_SOURCES = {
    "visit": "SELECT v.shop_id, v.id FROM visits v",
    "pet": "SELECT c.shop_id, p.id FROM pets p JOIN customers c ON c.id = p.customer_id WHERE c.deleted_at IS NULL",
    "customer": "SELECT c.shop_id, c.id FROM customers c WHERE c.deleted_at IS NULL",
}
# 지금 있는 검색 문서가 가리키는 대상 — 지병은 아이로 묶인다(search/domain/services/targets.py 와 같은 규칙).
_ORPHANS = {
    "visit": "SELECT DISTINCT d.shop_id, d.source_id FROM search_documents d "
             "WHERE d.kind IN ('care_note', 'internal_note', 'visit_memo')",
    "pet": "SELECT DISTINCT d.shop_id, CASE WHEN d.kind = 'condition_note' THEN d.pet_id ELSE d.source_id END "
           "FROM search_documents d WHERE d.kind IN ('pet_memo', 'condition_note')",
    "customer": "SELECT DISTINCT d.shop_id, d.source_id FROM search_documents d WHERE d.kind = 'customer_memo'",
}
_ENQUEUE = (
    "INSERT INTO search_jobs (shop_id, scope, ref_id, enqueued_at, next_attempt_at) "
    "SELECT t.shop_id, :scope, t.ref_id, :now, :now FROM ({source}) AS t(shop_id, ref_id) "
    "WHERE (CAST(:shop AS BIGINT) IS NULL OR t.shop_id = :shop) AND t.ref_id IS NOT NULL "
    "ON CONFLICT ON CONSTRAINT uq_search_jobs_target DO UPDATE "
    "SET generation = search_jobs.generation + 1, attempts = 0, enqueued_at = :now, next_attempt_at = :now"
)


async def enqueue_all(session: AsyncSession, shop_id: int | None = None, purge_orphans: bool = False) -> dict[str, int]:
    """대상을 줄에 넣고 scope 마다 넣은(또는 세대를 올린) 줄 수를 돌려준다. 커밋은 부르는 쪽이 한다."""
    now = datetime.now(timezone.utc)
    counts = {scope: 0 for scope in _SOURCES}
    for sources in (_SOURCES, _ORPHANS if purge_orphans else {}):
        for scope, source in sources.items():
            result = await session.execute(
                text(_ENQUEUE.format(source=source)), {"scope": scope, "now": now, "shop": shop_id})
            counts[scope] += result.rowcount
    return counts


async def _run(shop_id: int | None, purge_orphans: bool) -> dict[str, int]:
    engine = create_async_engine(DATABASE_URL, hide_parameters=True)
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            counts = await enqueue_all(session, shop_id, purge_orphans)
            await session.commit()
            return counts
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="기록 검색의 문서를 원본에 다시 맞춘다")
    parser.add_argument("--shop", type=int, default=None, help="그 매장만")
    parser.add_argument("--purge-orphans", action="store_true", help="원본이 사라진 문서도 지우게 한다")
    args = parser.parse_args()
    counts = asyncio.run(_run(args.shop, args.purge_orphans))
    print(f"다시 색인할 줄에 넣었습니다 — 방문 {counts['visit']}, 반려동물 {counts['pet']}, 고객 {counts['customer']}. "
          "색인기(backend)가 차례로 맞춥니다.")


if __name__ == "__main__":
    main()
