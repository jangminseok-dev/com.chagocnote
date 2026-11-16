from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from guardian.app.dtos.family_dto import EndAllFamilyCommand
from guardian.app.ports.input.end_all_family_use_case import EndAllFamilyUseCase
from guardian.app.ports.output.family_invite_repository import FamilyInviteRepository
from guardian.app.ports.output.guardian_link_repository import GuardianLinkRepository
from guardian.app.services.family_links import locked_primary


class EndAllFamilyInteractor(EndAllFamilyUseCase):
    """기본 보호자가 가족을 모두 끊고 안 쓴 초대를 죽인다. 잠금: 기본 연결 행 → 가족 초대 행 → 가족 연결 행."""

    def __init__(self, links: GuardianLinkRepository, invites: FamilyInviteRepository, now: Callable[[], datetime]) -> None:
        self._links = links
        self._invites = invites
        self._now = now

    async def end_all(self, command: EndAllFamilyCommand) -> None:
        primary = await locked_primary(self._links, command.user_id, command.link_id)
        now = self._now()
        await self._invites.revoke_unused([primary.id], now)
        await self._links.end_family([primary.id], "primary", now)
