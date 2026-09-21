from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.shop_context import ShopContext
from tenancy.app.dtos.shop_access_record import ShopAccessRecord
from tenancy.domain.entities.member import Member
from tenancy.domain.value_objects.role_code import RoleCode


class MemberRepository(ABC):
    @abstractmethod
    async def find_access(self, shop_id: int, user_id: int) -> ShopAccessRecord | None:
        """지금 속해 있는 멤버만 찾는다. 내보낸 멤버는 None."""

    @abstractmethod
    async def add(self, shop_id: int, user_id: int, role: RoleCode) -> Member:
        """이미 속해 있으면 AlreadyMemberError."""

    @abstractmethod
    async def list_active(self, ctx: ShopContext) -> list[Member]: ...

    @abstractmethod
    async def get_active(self, ctx: ShopContext, member_id: int) -> Member | None: ...

    @abstractmethod
    async def count_owners(self, ctx: ShopContext) -> int:
        """사장 행을 잠그고 센다. 두 사장이 동시에 서로를 낮춰 사장이 0명이 되는 일을 막는다."""

    @abstractmethod
    async def change_role(self, ctx: ShopContext, member_id: int, role: RoleCode) -> None: ...

    @abstractmethod
    async def remove(self, ctx: ShopContext, member_id: int) -> None: ...
