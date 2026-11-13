from __future__ import annotations

from fastapi import Depends

from core.config import REPORT_LINK_KEY
from core.database import DbSession
from hub.app.ports.report_link_port import ReportLinkPort
from hub.app.ports.shop_profile_port import ShopProfilePort
from visit.app.use_cases.resolve_report_link_interactor import ResolveReportLinkInteractor
from visit.dependencies.hub_ports import get_shop_profile
from visit.dependencies.visit_wiring import build_record_repository, build_report_repository
from visit.domain.services.visit_schedule import utc_now


def get_resolve_report_link_use_case(
    db: DbSession, shops: ShopProfilePort = Depends(get_shop_profile),
) -> ReportLinkPort:
    """허브 ReportLinkPort 의 구현 — 진입점이 guardian 의 자리에 꽂는다."""
    return ResolveReportLinkInteractor(
        reports=build_report_repository(db), records=build_record_repository(db), shops=shops, now=utc_now,
        link_key=REPORT_LINK_KEY,
    )
