from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone

from tenancy.app.dtos.create_invite_dto import CreatedInvite, CreateInviteCommand
from tenancy.app.ports.input.create_invite_use_case import CreateInviteUseCase
from tenancy.app.ports.output.invite_repository import InviteRepository
from tenancy.domain.services.invite_code import INVITE_TTL, generate_invite_code, hash_invite_code
from tenancy.domain.value_objects.role_code import RoleCode


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CreateInviteInteractor(CreateInviteUseCase):
    """직원용 초대만 만든다. 사장을 늘리려면 합류한 뒤 역할을 바꾼다."""

    def __init__(self, invites: InviteRepository, now: Callable[[], datetime] = _utcnow) -> None:
        self._invites = invites
        self._now = now

    async def create(self, command: CreateInviteCommand) -> CreatedInvite:
        code = generate_invite_code()
        expires_at = self._now() + INVITE_TTL
        await self._invites.create(
            command.ctx, RoleCode.STAFF, hash_invite_code(code), expires_at, max_uses=1
        )
        return CreatedInvite(code=code, role=RoleCode.STAFF.value, expires_at=expires_at)
