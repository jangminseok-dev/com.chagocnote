from __future__ import annotations

from core.database import DbSession
from guardian.app.use_cases.resolve_guardian_access_interactor import ResolveGuardianAccessInteractor
from guardian.dependencies.guardian_wiring import build_link_repository
from hub.app.ports.guardian_access_port import GuardianAccessPort


def get_resolve_guardian_access_use_case(db: DbSession) -> GuardianAccessPort:
    """허브 GuardianAccessPort 의 구현 — 진입점이 core/guardian_guard 의 자리에 꽂는다."""
    return ResolveGuardianAccessInteractor(build_link_repository(db))
