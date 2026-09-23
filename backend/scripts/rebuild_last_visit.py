"""고객 목록 '최근 방문순'의 키(customer_search_entries.last_visit_at)를 원본(visits)에서 모두 다시 맞춘다.

이 칸은 역정규화다(설계 5.3). 원본이 visit 스포크의 방문이라 복구 스크립트도 visit 쪽 값으로 계산한다 —
customer 의 검색 줄 재생성(rebuild_customer_search.py)은 이 칸을 건드리지 않는다. 여러 번 실행해도 결과가 같다.
고객마다 고객 행을 먼저 FOR UPDATE 로 잠근다 — 방문을 쓰는 유스케이스와 같은 순서(고객 행 → 방문 행)다.
고객 하나가 끝날 때마다 커밋해 잠금을 짧게 쥔다. 익명화한 고객은 검색 줄이 없어 아무것도 하지 않는다.
사용: cd infra && docker compose run --rm backend python scripts/rebuild_last_visit.py
"""
from __future__ import annotations

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.config import DATABASE_URL
from customer.adapter.outbound.orm.customer_orm import CustomerOrm
from customer.adapter.outbound.pg.customer_search_pg_adapter import CustomerSearchPgAdapter
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.outbound.pg.visit_pg_repository import VisitPgRepository


async def rebuild_all(session: AsyncSession) -> int:
    """모든 고객의 마지막 방문 시각을 원본에서 다시 넣고, 다룬 고객 수를 돌려준다. 고객마다 짧게 커밋한다."""
    search, visits = CustomerSearchPgAdapter(session), VisitPgRepository(session)
    rows = (await session.execute(select(CustomerOrm.id, CustomerOrm.shop_id).order_by(CustomerOrm.id))).all()
    for customer_id, shop_id in rows:
        # 사람의 요청이 아니라 운영 작업이다. 멤버·권한 없이 그 고객의 매장으로만 범위를 정한다.
        ctx = ShopContext(shop_id=shop_id, member_id=0, role="system", permissions=frozenset())
        await session.execute(
            select(CustomerOrm.id)
            .where(CustomerOrm.id == customer_id, CustomerOrm.shop_id == shop_id)
            .with_for_update()
        )
        await search.set_last_visit(ctx, customer_id, await visits.latest_completed_start(ctx, customer_id))
        await session.commit()
    return len(rows)


async def _run() -> int:
    engine = create_async_engine(DATABASE_URL, hide_parameters=True)
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            return await rebuild_all(session)
    finally:
        await engine.dispose()


def main() -> None:
    print(f"고객 {asyncio.run(_run())}명의 마지막 방문 시각을 다시 맞췄습니다.")


if __name__ == "__main__":
    main()
