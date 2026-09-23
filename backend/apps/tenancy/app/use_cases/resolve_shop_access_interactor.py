from __future__ import annotations

from hub.app.dtos.shop_context import ShopContext
from hub.app.ports.shop_access_port import ShopAccessPort
from tenancy.app.ports.output.member_repository import MemberRepository
from tenancy.domain.errors import NotAMemberError, ShopClosedError, ShopSuspendedError


class ResolveShopAccessInteractor(ShopAccessPort):
    """허브의 ShopAccessPort 구현. 입력 포트가 곧 허브 포트다."""

    def __init__(self, members: MemberRepository) -> None:
        self._members = members

    async def resolve(self, user_id: int, shop_id: int) -> ShopContext:
        record = await self._members.find_access(shop_id, user_id)
        if record is None:
            # 매장이 없는 경우와 소속이 아닌 경우를 구분해 주지 않는다 (매장 존재 여부를 흘리지 않는다).
            raise NotAMemberError("이 매장의 멤버가 아닙니다.")
        if record.shop_closed:
            raise ShopClosedError("닫힌 매장입니다.")
        if record.shop_suspended:
            raise ShopSuspendedError("이용이 정지된 매장입니다.")
        return ShopContext(
            shop_id=shop_id,
            member_id=record.member_id,
            role=record.role,
            permissions=record.permissions,
            timezone=record.timezone,
        )
