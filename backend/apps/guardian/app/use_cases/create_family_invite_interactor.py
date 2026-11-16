from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from guardian.app.dtos.family_dto import CreateFamilyInviteCommand, FamilyInviteResult
from guardian.app.ports.input.create_family_invite_use_case import CreateFamilyInviteUseCase
from guardian.app.ports.output.claim_limiter_port import ClaimLimiterPort
from guardian.app.ports.output.family_invite_repository import FamilyInviteRepository
from guardian.app.ports.output.guardian_link_repository import GuardianLinkRepository
from guardian.app.ports.output.guardian_settings_repository import GuardianSettingsRepository
from guardian.app.services.family_links import locked_primary
from guardian.domain.errors import GuardianAccountInactiveError, GuardianFamilyFullError, TooManyGuardianRequestsError
from guardian.domain.services.family_rules import hash_code, invite_expires_at, new_invite_code
from hub.app.ports.active_user_guard_port import ActiveUserGuardPort


class CreateFamilyInviteInteractor(CreateFamilyInviteUseCase):
    """기본 보호자가 가족 초대를 만든다(⑫ 설계 3.5). 앞의 안 쓴 초대는 죽는다. 가족이 매장이 정한 수만큼 찼으면 409.

    잠금: 유저 행 → 기본 연결 행 → (가족 초대 행). 코드 원문은 돌려주기만 한다.
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

    async def create(self, command: CreateFamilyInviteCommand) -> FamilyInviteResult:
        if not await self._limiter.allow(command.user_id):
            raise TooManyGuardianRequestsError("잠시 후 다시 시도해 주세요.")
        if not await self._users.lock_active(command.user_id):
            raise GuardianAccountInactiveError("다시 로그인해 주세요.")
        primary = await locked_primary(self._links, command.user_id, command.link_id)
        count = (await self._links.family_counts([primary.id])).get(primary.id, 0)
        if count >= await self._settings.family_max(primary.shop_id):
            raise GuardianFamilyFullError("함께 볼 수 있는 가족이 다 찼습니다.")
        now = self._now()
        await self._invites.revoke_unused([primary.id], now)
        code = new_invite_code()
        invite = await self._invites.create(primary.id, hash_code(code), now, invite_expires_at(now))
        return FamilyInviteResult(code=code, expires_at=invite.expires_at)
