"""고객 검색 줄(customer_search_entries)을 원본(customers·pets)에서 모두 다시 만든다. 여러 번 실행해도 결과가 같다.

검색 줄은 역정규화 표라 원본과 어긋나면 이 스크립트로 복구한다(설계 6.4). 익명화한 고객의 줄은 지운다.
마지막 방문 시각(last_visit_at)은 원본이 visits 라 건드리지 않는다 — scripts/rebuild_last_visit.py 가 맞춘다.
고객마다 고객 행을 먼저 FOR UPDATE 로 잠근 뒤 다시 만든다 — "가족을 바꾸는 쓰기는 고객 행을 먼저
잠근다"는 전역 잠금 순서와 맞춘다. 살아 있는 고객만 잠그는 CustomerRepository.lock_active 는 익명화한
고객에게 쓸 수 없어(찾지 못해 CustomerNotFoundError) 여기서는 익명화 여부와 상관없이 고객 행을 직접
잠근다. 고객 하나가 끝날 때마다 커밋해 잠금을 짧게 쥔다.
사용: cd infra && docker compose run --rm backend python scripts/rebuild_customer_search.py
"""
from __future__ import annotations

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.config import DATABASE_URL
from customer.adapter.outbound.orm.customer_orm import CustomerOrm
from customer.adapter.outbound.pg.customer_search_pg_adapter import CustomerSearchPgAdapter
from hub.app.dtos.shop_context import ShopContext


async def rebuild_all(session: AsyncSession) -> int:
    """모든 고객(익명화한 고객 포함)의 줄을 다시 만들고, 다시 만든 고객 수를 돌려준다. 고객마다 짧게 커밋한다."""
    search = CustomerSearchPgAdapter(session)
    rows = (await session.execute(select(CustomerOrm.id, CustomerOrm.shop_id).order_by(CustomerOrm.id))).all()
    for customer_id, shop_id in rows:
        # 사람의 요청이 아니라 운영 작업이다. 멤버·권한 없이 그 고객의 매장으로만 범위를 정한다.
        ctx = ShopContext(shop_id=shop_id, member_id=0, role="system", permissions=frozenset())
        await session.execute(
            select(CustomerOrm.id)
            .where(CustomerOrm.id == customer_id, CustomerOrm.shop_id == shop_id)
            .with_for_update()
        )
        await search.rebuild_search_entry(ctx, customer_id)
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
    print(f"고객 {asyncio.run(_run())}명의 검색 줄을 다시 만들었습니다.")


if __name__ == "__main__":
    main()
