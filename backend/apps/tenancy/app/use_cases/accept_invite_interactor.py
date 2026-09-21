from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone

from tenancy.app.dtos.accept_invite_dto import AcceptInviteCommand, AcceptInviteResult
from tenancy.app.ports.input.accept_invite_use_case import AcceptInviteUseCase
from tenancy.app.ports.output.invite_attempt_limiter_port import InviteAttemptLimiterPort
from tenancy.app.ports.output.invite_repository import InviteRepository
from tenancy.app.ports.output.member_repository import MemberRepository
from tenancy.app.ports.output.shop_repository import ShopRepository
from tenancy.domain.errors import InviteInvalidError, ShopClosedError, TooManyAttemptsError
from tenancy.domain.services.invite_code import hash_invite_code

MAX_INVITE_ATTEMPTS_PER_MINUTE = 5


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AcceptInviteInteractor(AcceptInviteUseCase):
    def __init__(
        self, invites: InviteRepository, members: MemberRepository, shops: ShopRepository,
        limiter: InviteAttemptLimiterPort, now: Callable[[], datetime] = _utcnow,
    ) -> None:
        self._invites = invites
        self._members = members
        self._shops = shops
        self._limiter = limiter
        self._now = now

    async def accept(self, command: AcceptInviteCommand) -> AcceptInviteResult:
        # 8자리 코드를 마구 넣어 보는 것을 막는다. 성공·실패를 가리지 않고 센다.
        if await self._limiter.hit(command.user_id) > MAX_INVITE_ATTEMPTS_PER_MINUTE:
            raise TooManyAttemptsError("초대 코드 입력이 너무 잦습니다. 1분 뒤에 다시 시도해 주세요.")
        code_hash = hash_invite_code(command.code)
        shop_id = await self._invites.find_shop_id_by_code_hash(code_hash)
        if shop_id is None:
            raise InviteInvalidError("초대 코드를 확인해 주세요.")
        # 내보내기·강등·탈퇴와 같은 순서(매장 → 멤버 → 초대)로 잠근다. 순서가 다르면 서로 교착한다.
        await self._members.lock_membership_changes(shop_id)
        invite = await self._invites.find_by_code_hash_for_update(code_hash)
        invite.ensure_usable(self._now())
        shop = await self._shops.get_by_id(invite.shop_id)
        if shop.is_closed:
            raise ShopClosedError("닫힌 매장입니다.")
        member = await self._members.add(invite.shop_id, command.user_id, invite.role)
        await self._invites.mark_used(invite.id)
        return AcceptInviteResult(
            shop_id=shop.id, shop_name=shop.name, role=member.role.value, member_id=member.id
        )
