from __future__ import annotations

from hub.app.dtos.shop_context import ShopContext
from hub.app.errors import (
    WithdrawalOwnershipTransferRequiredError,
    WithdrawalShopCloseConfirmRequiredError,
)
from hub.app.ports.membership_lifecycle_port import MembershipLifecyclePort
from tenancy.app.ports.output.invite_repository import InviteRepository
from tenancy.app.ports.output.member_repository import MemberRepository
from tenancy.app.ports.output.shop_repository import ShopRepository
from tenancy.domain.value_objects.role_code import RoleCode


class ApplyWithdrawalInteractor(MembershipLifecyclePort):
    """허브의 MembershipLifecyclePort 구현. 입력 포트가 곧 허브 포트다.

    auth 의 탈퇴 요청과 같은 DB 세션·같은 트랜잭션에서 돈다. 막히면 허브 오류를 던지고(auth 는 tenancy 의
    도메인 오류를 모른다), 요청의 트랜잭션이 통째로 되돌아가므로 앞서 처리한 매장의 변경도 남지 않는다.
    """

    def __init__(
        self, members: MemberRepository, shops: ShopRepository, invites: InviteRepository
    ) -> None:
        self._members = members
        self._shops = shops
        self._invites = invites

    async def apply_withdrawal(self, user_id: int, close_sole_owned: bool) -> None:
        # 매장 ID 오름차순으로 온다. 이 순서대로 잠가야 다른 유저의 탈퇴와 교착하지 않는다.
        for membership in await self._members.list_active_for_user(user_id):
            ctx = ShopContext(
                shop_id=membership.shop_id, member_id=membership.id,
                role=membership.role.value, permissions=frozenset(),
            )
            await self._members.lock_membership_changes(ctx.shop_id)
            # 잠근 뒤에 다시 읽는다. 목록을 읽은 뒤로 역할이 바뀌었거나 내보내졌을 수 있다.
            current = await self._members.get_active(ctx, membership.id)
            if current is None:
                continue
            shop = await self._shops.get(ctx)
            if (
                not shop.is_closed
                and current.role is RoleCode.OWNER
                and await self._members.count_owners(ctx) == 1
            ):
                if await self._members.count_active(ctx) > 1:
                    raise WithdrawalOwnershipTransferRequiredError(
                        f"'{shop.name}'의 사장이 회원님뿐입니다. 다른 멤버를 먼저 사장으로 지정해 주세요."
                    )
                if not close_sole_owned:
                    raise WithdrawalShopCloseConfirmRequiredError(
                        f"탈퇴하면 '{shop.name}'도 함께 닫힙니다. 확인 후 다시 시도해 주세요."
                    )
                await self._shops.close(ctx)
            await self._members.remove(ctx, current.id)
            await self._invites.revoke_created_by(ctx, current.id)
