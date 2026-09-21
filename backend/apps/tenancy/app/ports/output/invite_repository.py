from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from hub.app.dtos.shop_context import ShopContext
from tenancy.domain.entities.invite import Invite
from tenancy.domain.value_objects.role_code import RoleCode


class InviteRepository(ABC):
    @abstractmethod
    async def create(
        self, ctx: ShopContext, role: RoleCode, code_hash: str, expires_at: datetime, max_uses: int
    ) -> Invite:
        """멤버가 만드는 초대. 만든 멤버는 ctx.member_id 로 남는다."""

    @abstractmethod
    async def create_owner_invite(self, shop_id: int, code_hash: str, expires_at: datetime) -> Invite:
        """운영자가 매장을 개설하며 만드는 사장용 첫 초대. 아직 멤버가 없어 컨텍스트도 없다."""

    @abstractmethod
    async def find_by_code_hash_for_update(self, code_hash: str) -> Invite | None:
        """행을 잠근다. 1회용 코드를 두 사람이 동시에 넣어도 한 사람만 통과한다."""

    @abstractmethod
    async def mark_used(self, invite_id: int) -> None: ...
