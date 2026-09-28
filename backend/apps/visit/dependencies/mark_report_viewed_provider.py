from __future__ import annotations

from fastapi import Depends

from core.config import REPORT_LINK_KEY
from core.database import DbSession
from hub.app.ports.shop_profile_port import ShopProfilePort
from visit.app.ports.input.mark_report_viewed_use_case import MarkReportViewedUseCase
from visit.app.use_cases.mark_report_viewed_interactor import MarkReportViewedInteractor
from visit.dependencies.hub_ports import get_shop_profile
from visit.dependencies.visit_wiring import build_public_report_limiter, build_report_repository
from visit.domain.services.visit_schedule import utc_now


def get_mark_report_viewed_use_case(
    db: DbSession, shops: ShopProfilePort = Depends(get_shop_profile)
) -> MarkReportViewedUseCase:
    return MarkReportViewedInteractor(
        reports=build_report_repository(db), shops=shops, limiter=build_public_report_limiter(), now=utc_now,
        link_key=REPORT_LINK_KEY,
    )
