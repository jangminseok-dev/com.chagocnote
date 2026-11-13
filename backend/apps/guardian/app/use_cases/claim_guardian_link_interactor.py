from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from guardian.app.dtos.claim_guardian_link_dto import ClaimGuardianLinkCommand, ClaimGuardianLinkResult
from guardian.app.ports.input.claim_guardian_link_use_case import ClaimGuardianLinkUseCase
from guardian.app.ports.output.claim_limiter_port import ClaimLimiterPort
from guardian.app.ports.output.guardian_link_repository import GuardianLinkRepository
from guardian.domain.errors import (
    GuardianAccountInactiveError,
    GuardianAlreadyLinkedError,
    ReportLinkClosedError,
    ReportLinkNotFoundError,
    TooManyGuardianRequestsError,
)
from hub.app.ports.active_user_guard_port import ActiveUserGuardPort
from hub.app.ports.report_link_port import ReportLinkPort

VERIFIED_BY_REPORT_LINK = "report_link"


class ClaimGuardianLinkInteractor(ClaimGuardianLinkUseCase):
    """받은 알림장 링크로 그 고객 카드와 계정을 잇는다(⑦ 설계 3·4절).

    링크는 매장이 그 보호자의 번호로 보낸 것이라 링크를 가진 것이 본인 확인을 대신한다 — 그래서 열려 있는
    링크로만 잇고, 고객 카드 하나에는 계정 하나만 잇는다. 맨 앞에서 유저 행을 잠근다: 탈퇴와 겹치면 기다렸다가
    탈퇴 뒤에는 거절한다(잠금 순서: 유저 행 → 보호자 연결 행). 동시에 두 계정이 같은 카드를 이으면 둘째는
    저장소의 부분 유일 색인이 막는다.
    """

    def __init__(
        self, links: GuardianLinkRepository, reports: ReportLinkPort, users: ActiveUserGuardPort,
        limiter: ClaimLimiterPort, now: Callable[[], datetime],
    ) -> None:
        self._links = links
        self._reports = reports
        self._users = users
        self._limiter = limiter
        self._now = now

    async def claim(self, command: ClaimGuardianLinkCommand) -> ClaimGuardianLinkResult:
        if not await self._limiter.allow(command.user_id):
            raise TooManyGuardianRequestsError("요청이 너무 잦습니다. 잠시 뒤에 다시 해 주세요.")
        if not await self._users.lock_active(command.user_id):
            raise GuardianAccountInactiveError("다시 로그인해 주세요.")
        target = await self._reports.resolve(command.token)
        if target is None:
            raise ReportLinkNotFoundError("알림장을 찾을 수 없습니다.")
        if not target.live:
            raise ReportLinkClosedError("닫힌 알림장입니다.")
        existing = await self._links.find_live_for_customer(target.shop_id, target.customer_id)
        if existing is not None:
            if existing.user_id == command.user_id:
                return ClaimGuardianLinkResult(link_id=existing.id, created=False)
            raise GuardianAlreadyLinkedError("이미 다른 계정에 연결된 고객입니다. 매장에 문의해 주세요.")
        created = await self._links.create(
            command.user_id, target.shop_id, target.customer_id, VERIFIED_BY_REPORT_LINK, self._now())
        return ClaimGuardianLinkResult(link_id=created.id, created=True)
