"""방문의 사실이 바뀐 뒤 customer 에 알리는 후속 처리 — 같은 트랜잭션 안에서, 방문 행을 잠근 채로.

둘이다. ① 완료가 생기거나 풀리면 그 보호자의 마지막 완료 방문 시작 시각(고객 목록 '최근 방문순'). 전이가 부른다.
② 기록에 몸무게를 적으면, 그 방문이 그 아이의 가장 최근 시작한 방문일 때 현재 몸무게. 기록 쓰기가 부른다.
유스케이스는 잠금·쓰기·후속 호출만 하고, 무엇을 언제 알릴지는 여기 한 곳에 둔다.
"""
from __future__ import annotations

from decimal import Decimal

from hub.app.dtos.shop_context import ShopContext
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from visit.app.ports.output.visit_history_repository import VisitHistoryRepository
from visit.domain.entities.visit import COMPLETED, Visit


def touches_completion(before: list[Visit], after: list[Visit]) -> bool:
    """전후 어느 쪽에든 완료 방문이 있는가 — 완료가 생기는·풀리는 전이와 완료 방문의 기록 수정(④-1)을 모두
    덮는다. 둘 다 완료여도 참이다(후속 처리는 멱등이라 다시 계산해도 된다)."""
    return any(v.status == COMPLETED for v in before) or any(v.status == COMPLETED for v in after)


async def apply_completion_effects(
    ctx: ShopContext, before: list[Visit], after: list[Visit],
    history: VisitHistoryRepository, directory: CustomerDirectoryPort,
) -> None:
    """완료를 건드렸으면 후속 처리를 한다. 아니면 아무것도 부르지 않는다."""
    if not touches_completion(before, after):
        return
    customer_id = after[0].customer_id
    latest = await history.latest_completed_start(ctx, customer_id)
    await directory.set_last_visit(ctx, customer_id, latest)


async def sync_pet_weight(
    ctx: ShopContext, visit: Visit, weight_kg: Decimal | None,
    history: VisitHistoryRepository, directory: CustomerDirectoryPort,
) -> None:
    """기록의 몸무게를 현재 몸무게로 넘긴다 — 그 아이의 가장 최근 시작한 방문의 기록일 때만.
    옛 기록을 고쳐도 현재 값은 바뀌지 않는다(설계 8절). 고객 행은 부르는 쪽이 이미 잠갔다."""
    if weight_kg is None or visit.pet_id is None:
        return
    if await history.latest_started_of_pet(ctx, visit.pet_id) == visit.id:
        await directory.set_pet_weight(ctx, visit.pet_id, weight_kg)
