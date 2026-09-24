from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.shop_context import ShopContext
from visit.domain.entities.visit import Visit


class VisitLookupRepository(ABC):
    """방문을 ID 로 찾고 잠근다. 모든 메서드가 ShopContext 의 매장으로 거른다.

    방문 리포지토리 다섯 포트 가운데 가장 작은 것 — 잠금 순서 서비스(`visit_locking.lock_visits`)와 상세·초안
    조회가 이것만 받는다. 쓰기 포트(`VisitWriteRepository`)가 이를 상속한다.
    """

    @abstractmethod
    async def get(self, ctx: ShopContext, visit_id: int) -> Visit:
        """없거나 다른 매장이면 VisitNotFoundError."""

    @abstractmethod
    async def get_many(self, ctx: ShopContext, visit_ids: list[int]) -> list[Visit]:
        """이 매장의 것만 돌려준다 — 모자라면 부르는 쪽이 없는 것으로 본다."""

    @abstractmethod
    async def lock(self, ctx: ShopContext, visit_ids: list[int]) -> list[Visit]:
        """방문 행을 ID 오름차순으로 FOR UPDATE 잠그고 다시 읽는다. 고객 행을 잠근 **뒤에** 부른다(설계 4.2).
        이 매장의 것만 돌려준다 — 모자라면 부르는 쪽이 없는 것으로 본다."""
