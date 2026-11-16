"""남은 일(⑬)을 세는 범위 — 하루 머리·달력·하루 마무리가 같다.

익명화한 고객의 방문은 기록·알림장을 쓸 수 없어(가족 잠금이 404) 끝낼 수 없으므로 남은 일이 아니다. 하루 목록과 하루
마무리는 이미 읽은 방문의 고객 요약(이름이 None)으로 가리고, 달력은 이 함수로 한 번 묻는다.
"""
from __future__ import annotations

from hub.app.dtos.shop_context import ShopContext
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from visit.domain.entities.visit import Visit


async def anonymized_customers(
    ctx: ShopContext, visits: list[Visit], directory: CustomerDirectoryPort
) -> frozenset[int]:
    """방문들의 고객 가운데 이름이 없는(익명화한) 고객. 방문이 없으면 묻지 않는다."""
    ids = sorted({v.customer_id for v in visits})
    if not ids:
        return frozenset()
    customers = (await directory.briefs(ctx, ids, [])).customers
    return frozenset(c for c in ids if c not in customers or customers[c].name is None)
