from __future__ import annotations

from abc import ABC, abstractmethod

from customer.domain.entities.condition_type import ConditionType


class ConditionTypeRepository(ABC):
    """정해진 질병 종류(마이그레이션 시드). 매장과 상관없는 표라 ShopContext 를 받지 않는다."""

    @abstractmethod
    async def list_all(self) -> list[ConditionType]:
        """칩 순서(sort_order)대로."""
