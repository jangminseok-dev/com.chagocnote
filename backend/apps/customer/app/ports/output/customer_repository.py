from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from customer.domain.entities.customer import Customer
from customer.domain.value_objects.customer_profile import CustomerProfile
from hub.app.dtos.shop_context import ShopContext


class CustomerRepository(ABC):
    """살아 있는 고객만 다룬다. 익명화한 고객은 어느 메서드에서도 없는 것으로 본다."""

    @abstractmethod
    async def find_active_by_phone(self, ctx: ShopContext, phone: str) -> Customer | None: ...

    @abstractmethod
    async def get_active(self, ctx: ShopContext, customer_id: int) -> Customer:
        """없거나 다른 매장이거나 익명화했으면 CustomerNotFoundError."""

    @abstractmethod
    async def lock_active(self, ctx: ShopContext, customer_id: int) -> Customer:
        """고객 행을 FOR UPDATE 로 잠그고 다시 읽는다. 가족(고객·반려동물·질병)을 바꾸는 유스케이스는 맨 앞에서 부른다."""

    @abstractmethod
    async def list_active(self, ctx: ShopContext, customer_ids: list[int]) -> list[Customer]: ...

    @abstractmethod
    async def create(self, ctx: ShopContext, profile: CustomerProfile) -> Customer:
        """번호가 살아 있는 다른 고객과 겹치면 CustomerPhoneTakenError."""

    @abstractmethod
    async def update(
        self, ctx: ShopContext, customer_id: int, profile: CustomerProfile, consent_changed: bool
    ) -> Customer:
        """consent_changed 일 때만 동의 시각을 새로 찍는다. 번호가 겹치면 CustomerPhoneTakenError."""

    @abstractmethod
    async def set_caution(
        self, ctx: ShopContext, customer_id: int, reason: str | None, until: date | None,
        member_id: int | None,
    ) -> Customer:
        """주의 표시를 단다(단 시각은 지금). 셋 다 None 이면 푼다. 소속이 아니면 CustomerNotFoundError."""

    @abstractmethod
    async def anonymize(self, ctx: ShopContext, customer_id: int) -> None:
        """개인정보를 지운다: 고객의 이름·전화·보조 연락처·메모, 반려동물의 이름·메모, 질병 행. 행과 틀은 남긴다."""
