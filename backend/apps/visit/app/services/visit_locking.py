"""방문을 쓰는 유스케이스의 공통 순서 — 고객 행(허브 포트) → 방문 행(ID 오름차순) 잠금 뒤 다시 읽기(설계 4.2)."""
from __future__ import annotations

from hub.app.dtos.shop_context import ShopContext
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from visit.app.ports.output.visit_repository import VisitRepository
from visit.domain.entities.visit import Visit
from visit.domain.errors import VisitGroupMismatchError, VisitNotFoundError


async def lock_visits(
    ctx: ShopContext, visit_ids: list[int], visits: VisitRepository, directory: CustomerDirectoryPort,
    pet_ids: tuple[int, ...] = (),
) -> list[Visit]:
    """visit_ids 의 방문을 잠그고 다시 읽은 목록(ID 순)을 돌려준다.

    모두 이 매장의 방문이어야 하고(아니면 VISIT_NOT_FOUND), 같은 보호자의 방문이어야 한다(아니면
    VISIT_GROUP_MISMATCH). pet_ids 는 가족 확인에 넘길 반려동물 — 새로 시간을 차지하게 되는 아이만 넘긴다.
    """
    found = await visits.get_many(ctx, visit_ids)
    if len(found) != len(set(visit_ids)):
        raise VisitNotFoundError("방문을 찾을 수 없습니다.")
    customers = {v.customer_id for v in found}
    if len(customers) != 1:
        raise VisitGroupMismatchError("같은 보호자의 방문만 한 번에 다룰 수 있습니다.")
    await directory.lock_family(ctx, customers.pop(), pet_ids)
    return sorted(await visits.lock(ctx, visit_ids), key=lambda v: v.id)
