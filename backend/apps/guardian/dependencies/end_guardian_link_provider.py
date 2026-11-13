from __future__ import annotations

from core.database import DbSession
from guardian.app.ports.input.end_guardian_link_use_case import EndGuardianLinkUseCase
from guardian.app.use_cases.end_guardian_link_interactor import EndGuardianLinkInteractor
from guardian.dependencies.guardian_wiring import build_link_repository, utc_now


def get_end_guardian_link_use_case(db: DbSession) -> EndGuardianLinkUseCase:
    return EndGuardianLinkInteractor(build_link_repository(db), now=utc_now)
