from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal

from customer.domain.entities.pet import Pet
from customer.domain.value_objects.pet_profile import PetProfile
from hub.app.dtos.shop_context import ShopContext


class PetRepository(ABC):
    """반려동물은 고객을 거쳐 매장에 속한다. 모든 메서드가 반려동물 → 고객(살아 있음) → 매장 순서로 소속을 거른다."""

    @abstractmethod
    async def get(self, ctx: ShopContext, pet_id: int) -> Pet:
        """없거나 다른 매장이거나 보호자가 익명화됐으면 PetNotFoundError."""

    @abstractmethod
    async def lock_owner(self, ctx: ShopContext, pet_id: int) -> int:
        """반려동물의 고객 행을 FOR UPDATE 로 잠그고 고객 ID 를 돌려준다. 소속이 아니면 PetNotFoundError."""

    @abstractmethod
    async def list_for_customers(self, ctx: ShopContext, customer_ids: list[int]) -> list[Pet]:
        """고객별로 등록 순서대로."""

    @abstractmethod
    async def add(self, ctx: ShopContext, customer_id: int, profile: PetProfile) -> Pet: ...

    @abstractmethod
    async def update(self, ctx: ShopContext, pet_id: int, profile: PetProfile) -> Pet:
        """질병 목록은 통째로 바꾼다."""

    @abstractmethod
    async def set_passed_away(self, ctx: ShopContext, pet_id: int, passed_away: bool) -> Pet: ...

    @abstractmethod
    async def set_weight(self, ctx: ShopContext, pet_id: int, weight_kg: Decimal) -> None:
        """현재 몸무게만 바꾼다(미용 기록이 알려 준 값). 소속이 아니면 아무것도 바꾸지 않는다."""

    @abstractmethod
    async def set_grooming_cycle(self, ctx: ShopContext, pet_id: int, weeks: int | None) -> None:
        """직접 정한 미용 주기(⑬). None 이면 지운다(계산한 값으로 돌아간다)."""

    @abstractmethod
    async def set_revisit_nudged(self, ctx: ShopContext, pet_id: int, on: date) -> None:
        """다시 올 때라고 안내한 날(⑬)."""

    @abstractmethod
    async def revisit_facts(self, ctx: ShopContext, pet_ids: list[int]) -> dict[int, tuple[int | None, date | None]]:
        """{반려동물 ID: (직접 정한 주기, 안내한 날)} — 이 매장의 아이만. 질의 하나."""

    @abstractmethod
    async def set_grooming_consent(
        self, ctx: ShopContext, pet_id: int, received_on: date | None, member_id: int | None,
        signature_id: int | None = None,
    ) -> Pet:
        """미용 동의를 받은 날과 적은 멤버. 둘 다 None 이면 지운다. 소속이 아니면 PetNotFoundError.

        signature_id 는 그날을 찍은 서명이다(⑪) — 손으로 적은 동의면 None 이고, 부를 때마다 덮어쓴다.
        """

    @abstractmethod
    async def count_for_customer(self, ctx: ShopContext, customer_id: int) -> int: ...

    @abstractmethod
    async def delete(self, ctx: ShopContext, pet_id: int) -> None:
        """행을 지운다. 질병 행은 외래 키의 ON DELETE CASCADE 로 함께 지워진다."""
