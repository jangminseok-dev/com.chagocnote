"""완료가 생기거나 풀린 뒤의 후속 처리 — 같은 트랜잭션 안에서, 방문 행을 잠근 채로.

지금은 하나다: 그 보호자의 마지막 완료 방문 시작 시각을 customer 에 넘긴다(고객 목록 '최근 방문순').
④ 기록 슬라이스는 몸무게 동기화를 여기에 더한다 — 전이·기록 두 유스케이스가 같은 함수를 부르므로 후속 처리가
한 곳에 남는다(단일 책임: 전이 인터랙터는 잠금·전이·후속 호출만 한다).
"""
from __future__ import annotations

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
