from __future__ import annotations

from core.database import DbSession
from guardian.app.ports.input.end_customer_guardian_link_use_case import EndCustomerGuardianLinkUseCase
from guardian.app.use_cases.end_customer_guardian_link_interactor import EndCustomerGuardianLinkInteractor
from guardian.dependencies.guardian_wiring import build_invite_repository, build_link_repository, utc_now


def get_end_customer_guardian_link_use_case(db: DbSession) -> EndCustomerGuardianLinkUseCase:
    return EndCustomerGuardianLinkInteractor(build_link_repository(db), now=utc_now, invites=build_invite_repository(db))
