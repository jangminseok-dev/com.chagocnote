from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class HistoryAsk:
    """[pet_id] 의, [before] 보다 앞에 시작한 완료 방문을 묻는다. key 는 묻는 쪽의 식별자다."""

    key: int
    pet_id: int
    before: datetime


@dataclass(frozen=True)
class NoShowAsk:
    """[customer_id] 의, since <= 시작 시각 < until 인 노쇼를 묻는다."""

    key: int
    customer_id: int
    since: datetime
    until: datetime


class VisitCheckRepository(ABC):
    """확인할 것(③-B)의 방문 쪽 사실. 물음이 몇 개든 메서드 하나가 질의 한 번이다."""

    @abstractmethod
    async def last_completed(self, ctx: ShopContext, asks: list[HistoryAsk]) -> dict[int, datetime | None]:
        """key → 그 아이의 [before] 앞 마지막 완료 방문의 시작 시각. 없으면 None. 모든 key 가 들어 있다."""

    @abstractmethod
    async def no_shows(self, ctx: ShopContext, asks: list[NoShowAsk]) -> dict[int, int]:
        """key → 창 안의 노쇼 수. 모든 key 가 들어 있다(없으면 0)."""
