from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from guardian.app.dtos.end_guardian_link_dto import EndGuardianLinkCommand
from guardian.app.ports.input.end_guardian_link_use_case import EndGuardianLinkUseCase
from guardian.app.ports.output.family_invite_repository import FamilyInviteRepository
from guardian.app.ports.output.guardian_link_repository import GuardianLinkRepository
from guardian.app.services.family_links import end_primary
from guardian.domain.errors import GuardianLinkNotFoundError


class EndGuardianLinkInteractor(EndGuardianLinkUseCase):
    """보호자가 자기 연결을 끊는다. 없는 연결·남의 연결·끝난 연결은 구분하지 않고 404 다."""

    def __init__(
        self, links: GuardianLinkRepository, now: Callable[[], datetime], invites: FamilyInviteRepository | None = None,
    ) -> None:
        self._links = links
        self._now = now
        self._invites = invites

    async def end_link(self, command: EndGuardianLinkCommand) -> None:
        """가족이 끊으면 자기 연결만, 기본 보호자가 끊으면 가족과 안 쓴 초대까지(⑫). 늘 기본 연결 행부터 잠근다."""
        link = await self._links.get_live(command.user_id, command.link_id)
        if link is None:
            raise GuardianLinkNotFoundError("연결을 찾을 수 없습니다.")
        now = self._now()
        if link.is_family:
            await self._links.lock_primary(link.parent_link_id)
            if not await self._links.end(link.id, "guardian", now):
                raise GuardianLinkNotFoundError("연결을 찾을 수 없습니다.")
            return
        primary = await self._links.lock_primary(link.id)
        if primary is None or self._invites is None:
            if primary is None or not await self._links.end(link.id, "guardian", now):
                raise GuardianLinkNotFoundError("연결을 찾을 수 없습니다.")
            return
        await end_primary(self._links, self._invites, primary, "guardian", now)
