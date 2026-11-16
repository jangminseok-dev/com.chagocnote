from __future__ import annotations

from core.database import DbSession
from guardian.app.use_cases.end_guardian_links_interactor import EndGuardianLinksInteractor
from guardian.dependencies.guardian_wiring import build_invite_repository, build_link_repository, utc_now
from hub.app.ports.guardian_lifecycle_port import GuardianLifecyclePort


def get_end_guardian_links_use_case(db: DbSession) -> GuardianLifecyclePort:
    """허브 GuardianLifecyclePort 의 구현 — 진입점이 auth(탈퇴)와 customer(익명화)의 자리에 꽂는다."""
    return EndGuardianLinksInteractor(build_link_repository(db), now=utc_now, invites=build_invite_repository(db))
