from __future__ import annotations

from core.database import DbSession
from guardian.app.ports.input.get_customer_guardian_link_use_case import GetCustomerGuardianLinkUseCase
from guardian.app.use_cases.get_customer_guardian_link_interactor import GetCustomerGuardianLinkInteractor
from guardian.dependencies.guardian_wiring import build_link_repository


def get_get_customer_guardian_link_use_case(db: DbSession) -> GetCustomerGuardianLinkUseCase:
    return GetCustomerGuardianLinkInteractor(build_link_repository(db))
