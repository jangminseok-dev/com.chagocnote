from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.family_brief import CustomerBrief, PetBrief
from hub.app.dtos.shop_context import ShopContext


class FamilyBriefRepository(ABC):
    """다른 스포크에 보여 줄 요약. CustomerRepository 와 달리 익명화한 고객도 틀을 돌려준다(이름은 None) —
    방문 기록은 익명화한 뒤에도 남기 때문이다(설계 5.4)."""

    @abstractmethod
    async def list_customer_briefs(self, ctx: ShopContext, customer_ids: list[int]) -> list[CustomerBrief]: ...

    @abstractmethod
    async def list_pet_briefs(self, ctx: ShopContext, pet_ids: list[int]) -> list[PetBrief]: ...
