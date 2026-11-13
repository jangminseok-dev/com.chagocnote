from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from guardian.app.dtos.end_guardian_link_dto import EndGuardianLinkCommand
from guardian.app.ports.input.end_guardian_link_use_case import EndGuardianLinkUseCase
from guardian.app.ports.output.guardian_link_repository import GuardianLinkRepository
from guardian.domain.errors import GuardianLinkNotFoundError


class EndGuardianLinkInteractor(EndGuardianLinkUseCase):
    """보호자가 자기 연결을 끊는다. 없는 연결·남의 연결·끝난 연결은 구분하지 않고 404 다."""

    def __init__(self, links: GuardianLinkRepository, now: Callable[[], datetime]) -> None:
        self._links = links
        self._now = now

    async def end_link(self, command: EndGuardianLinkCommand) -> None:
        link = await self._links.get_live(command.user_id, command.link_id)
        if link is None or not await self._links.end(link.id, "guardian", self._now()):
            raise GuardianLinkNotFoundError("연결을 찾을 수 없습니다.")
