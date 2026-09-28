from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext
from visit.app.dtos.report_view_dto import ReportLinkView, ReportView


@dataclass(frozen=True)
class GetVisitReportQuery:
    ctx: ShopContext
    visit_id: int


@dataclass(frozen=True)
class VisitReportPreview:
    report: ReportView     # 보호자가 볼 내용에 뺀 사진·영상(hidden)을 더한 것. 매장의 설정은 report.settings
    link: ReportLinkView   # 시각은 매장 시간대
