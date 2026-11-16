from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from guardian.app.dtos.family_dto import JoinFamilyCommand, JoinFamilyResult
from guardian.app.ports.input.join_family_use_case import JoinFamilyUseCase
from guardian.app.ports.output.claim_limiter_port import ClaimLimiterPort
from guardian.app.ports.output.family_invite_repository import FamilyInviteRepository
from guardian.app.ports.output.guardian_link_repository import GuardianLinkRepository
from guardian.app.ports.output.guardian_settings_repository import GuardianSettingsRepository
from guardian.domain.errors import (
    GuardianAccountInactiveError, GuardianFamilyFullError, GuardianInviteNotFoundError, TooManyGuardianRequestsError,
)
from guardian.domain.services.family_rules import hash_code, is_code_shaped
from hub.app.ports.active_user_guard_port import ActiveUserGuardPort


class JoinFamilyInteractor(JoinFamilyUseCase):
    """초대를 받은 가족이 로그인해 잇는다(⑫ 설계 3.5). 기본 연결 아래에 가족 연결이 생긴다.

    잠금: 유저 행 → 기본 연결 행 → 가족 초대 행 → (가족 연결 행). 기본 연결 행을 쥔 채 수를 세므로 동시에 와도
    수를 넘지 않고, 같은 초대로 둘이 와도 하나만 된다. 없음·쓴·죽은·기간 지난 코드와 끝난 기본 연결은 모두 404.
    기본 보호자 자신이거나 이미 그 가족이면 초대를 쓰지 않고 그 연결을 돌려준다(200).
    """

    def __init__(
        self, links: GuardianLinkRepository, invites: FamilyInviteRepository, settings: GuardianSettingsRepository,
        users: ActiveUserGuardPort, limiter: ClaimLimiterPort, now: Callable[[], datetime],
    ) -> None:
        self._links = links
        self._invites = invites
        self._settings = settings
        self._users = users
        self._limiter = limiter
        self._now = now

    async def join(self, command: JoinFamilyCommand) -> JoinFamilyResult:
        if not await self._limiter.allow(command.user_id):
            raise TooManyGuardianRequestsError("잠시 후 다시 시도해 주세요.")
        if not await self._users.lock_active(command.user_id):
            raise GuardianAccountInactiveError("다시 로그인해 주세요.")
        missing = GuardianInviteNotFoundError("초대를 찾을 수 없습니다.")
        if not is_code_shaped(command.code):
            raise missing
        found = await self._invites.find(hash_code(command.code))
        primary = None if found is None else await self._links.lock_primary(found.link_id)
        if found is None or primary is None:
            raise missing
        if primary.user_id == command.user_id:
            return JoinFamilyResult(link_id=primary.id, created=False)
        existing = await self._links.find_family(primary.id, command.user_id)
        if existing is not None:
            return JoinFamilyResult(link_id=existing.id, created=False)
        now = self._now()
        invite = await self._invites.lock(found.id)
        if invite is None or not invite.is_usable(now):
            raise missing
        count = (await self._links.family_counts([primary.id])).get(primary.id, 0)
        if count >= await self._settings.family_max(primary.shop_id):
            raise GuardianFamilyFullError("함께 볼 수 있는 가족이 다 찼습니다.")
        family = await self._links.create_family(command.user_id, primary, now)
        await self._invites.mark_used(invite.id, now)
        return JoinFamilyResult(link_id=family.id, created=True)
