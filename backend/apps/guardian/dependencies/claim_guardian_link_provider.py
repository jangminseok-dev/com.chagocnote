from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from guardian.app.ports.input.claim_guardian_link_use_case import ClaimGuardianLinkUseCase
from guardian.app.use_cases.claim_guardian_link_interactor import ClaimGuardianLinkInteractor
from guardian.dependencies.guardian_wiring import build_claim_limiter, build_link_repository, utc_now
from guardian.dependencies.hub_ports import get_active_user_guard, get_report_link
from hub.app.ports.active_user_guard_port import ActiveUserGuardPort
from hub.app.ports.report_link_port import ReportLinkPort


def get_claim_guardian_link_use_case(
    db: DbSession,
    reports: ReportLinkPort = Depends(get_report_link),
    users: ActiveUserGuardPort = Depends(get_active_user_guard),
) -> ClaimGuardianLinkUseCase:
    return ClaimGuardianLinkInteractor(
        links=build_link_repository(db), reports=reports, users=users, limiter=build_claim_limiter(), now=utc_now)
