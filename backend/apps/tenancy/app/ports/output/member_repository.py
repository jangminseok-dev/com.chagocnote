from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.membership_summary import MembershipSummary
from hub.app.dtos.shop_context import ShopContext
from tenancy.app.dtos.shop_access_record import ShopAccessRecord
from tenancy.domain.entities.member import Member
from tenancy.domain.value_objects.role_code import RoleCode


class MemberRepository(ABC):
    @abstractmethod
    async def lock_membership_changes(self, shop_id: int) -> None:
        """매장 행을 잠가 같은 매장의 역할 변경·내보내기·초대 수락·탈퇴를 직렬화한다.

        마지막 사장 규칙을 지키고, 모든 경로가 매장 → 멤버 → 초대 순으로 잠가 교착하지 않게 하려는 것이다.
        대상을 읽기 **전에** 부른다. 데이터를 읽는 메서드가 아니라서 ShopContext 를 받지 않는다 —
        초대 수락과 탈퇴는 컨텍스트 없이 잠가야 한다.
        """

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
        """지금 살아 있는 사장 행을 잠그고 센다. lock_membership_changes 뒤에 부른다."""

    @abstractmethod
    async def change_role(self, ctx: ShopContext, member_id: int, role: RoleCode) -> None: ...

    @abstractmethod
    async def remove(self, ctx: ShopContext, member_id: int) -> None: ...

    @abstractmethod
    async def list_for_user(self, user_id: int) -> list[MembershipSummary]:
        """유저 기준 조회라 매장 컨텍스트가 없다. 내보내진 소속과 닫힌 매장은 뺀다."""

    @abstractmethod
    async def list_active_for_user(self, user_id: int) -> list[Member]:
        """탈퇴용. 유저가 지금 속해 있는 모든 소속을 매장 ID 오름차순으로 돌려준다 (닫힌 매장 포함).

        순서가 곧 잠금 순서다. 두 유저의 탈퇴가 서로 다른 순서로 매장을 잠그면 교착한다.
        """

    @abstractmethod
    async def count_active(self, ctx: ShopContext) -> int:
        """지금 속해 있는 멤버 수. lock_membership_changes 뒤에 부른다."""
