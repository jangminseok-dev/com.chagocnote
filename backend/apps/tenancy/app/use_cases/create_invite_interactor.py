from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone

from tenancy.app.dtos.create_invite_dto import CreatedInvite, CreateInviteCommand
from tenancy.app.ports.input.create_invite_use_case import CreateInviteUseCase
from tenancy.app.ports.output.invite_repository import InviteRepository
from tenancy.app.ports.output.member_repository import MemberRepository
from tenancy.domain.services.actor_guard import ensure_actor_unchanged
from tenancy.domain.services.invite_code import INVITE_TTL, generate_invite_code, hash_invite_code
from tenancy.domain.value_objects.role_code import RoleCode


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CreateInviteInteractor(CreateInviteUseCase):
    """직원용 초대만 만든다. 사장을 늘리려면 합류한 뒤 역할을 바꾼다."""

    def __init__(
        self, members: MemberRepository, invites: InviteRepository,
        now: Callable[[], datetime] = _utcnow,
    ) -> None:
        self._members = members
        self._invites = invites
        self._now = now

    async def create(self, command: CreateInviteCommand) -> CreatedInvite:
        # 권한 확인(요청 가드)과 초대 생성 사이에 그 멤버가 내보내지거나 낮춰질 수 있다. 초대를 만들기
        # 전에 매장 단위로 직렬화하고 행위자를 다시 읽는다. 이 잠금이 없으면 INSERT 가 외래 키의
        # 암묵적 잠금으로 기다렸다가, 내보내기의 초대 무효화가 끝난 뒤에 살아 있는 초대를 남긴다.
        await self._members.lock_membership_changes(command.ctx.shop_id)
        actor = await self._members.get_active(command.ctx, command.ctx.member_id)
        ensure_actor_unchanged(actor, command.ctx.role)
        code = generate_invite_code()
        expires_at = self._now() + INVITE_TTL
        await self._invites.create(
            command.ctx, RoleCode.STAFF, hash_invite_code(code), expires_at, max_uses=1
        )
        return CreatedInvite(code=code, role=RoleCode.STAFF.value, expires_at=expires_at)
