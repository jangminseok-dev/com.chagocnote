from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext
from visit.domain.entities.visit import Visit


@dataclass(frozen=True)
class FeedPage:
    visits: list[Visit]
    next_cursor: str | None   # 없으면 마지막 쪽이다


class VisitFeedRepository(ABC):
    """완료 방문을 완료 시각 역순으로 이어 읽는다(피드). 모든 메서드가 ShopContext 의 매장으로 거른다.

    방문 리포지토리의 여섯째 축 — 하루·달력(게시판)은 시작 시각 범위로, 피드는 완료 시각 순서로 읽는다.
    """

    @abstractmethod
    async def list_completed(
        self, ctx: ShopContext, cursor: str | None, limit: int, pet_id: int | None
    ) -> FeedPage:
        """완료 시각, 같으면 방문 ID 역순. pet_id 가 있으면 그 아이의 방문만. 커서가 틀리면 VisitInputError."""
