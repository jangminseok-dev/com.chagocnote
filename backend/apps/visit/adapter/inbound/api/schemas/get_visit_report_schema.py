from __future__ import annotations

from pydantic import BaseModel

from visit.adapter.inbound.api.schemas.get_report_settings_schema import ReportSettingsSchema
from visit.adapter.inbound.api.schemas.report_view_schema import ReportLinkSchema, ReportSchema
from visit.app.dtos.get_visit_report_dto import VisitReportPreview


class VisitReportSchema(BaseModel):
    report: ReportSchema
    link: ReportLinkSchema
    settings: ReportSettingsSchema   # 앱이 "함께 보이는 항목"을 이것으로 그린다

    @classmethod
    def of(cls, view: VisitReportPreview) -> VisitReportSchema:
        return cls(
            report=ReportSchema.model_validate(view.report, from_attributes=True),
            link=ReportLinkSchema.model_validate(view.link, from_attributes=True),
            settings=ReportSettingsSchema.of(view.report.settings),
        )
