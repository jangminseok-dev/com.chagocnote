from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from guardian.app.dtos.family_dto import EndFamilyMemberCommand
from guardian.app.ports.input.end_family_member_use_case import EndFamilyMemberUseCase
from guardian.app.ports.output.guardian_link_repository import GuardianLinkRepository
from guardian.app.services.family_links import locked_primary
from guardian.domain.errors import GuardianLinkNotFoundError


class EndFamilyMemberInteractor(EndFamilyMemberUseCase):
    """기본 보호자가 가족 한 명을 끊는다. 잠금: 기본 연결 행 → 그 가족 연결 행. 남의 것·없는 것은 404."""

    def __init__(self, links: GuardianLinkRepository, now: Callable[[], datetime]) -> None:
        self._links = links
        self._now = now

    async def end_member(self, command: EndFamilyMemberCommand) -> None:
        primary = await locked_primary(self._links, command.user_id, command.link_id)
        family = await self._links.get_family(primary.id, command.family_id)
        if family is None or not await self._links.end(family.id, "primary", self._now()):
            raise GuardianLinkNotFoundError("연결을 찾을 수 없습니다.")
