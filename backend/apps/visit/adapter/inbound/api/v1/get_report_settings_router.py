from fastapi import APIRouter, Depends

from core.shop_guard import get_shop_context
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.schemas.get_report_settings_schema import ReportSettingsSchema
from visit.app.dtos.get_report_settings_dto import GetReportSettingsQuery
from visit.app.ports.input.get_report_settings_use_case import GetReportSettingsUseCase
from visit.dependencies.get_report_settings_provider import get_get_report_settings_use_case

get_report_settings_router = APIRouter(prefix="/v1/shops", tags=["visits"])


@get_report_settings_router.get("/{shop_id}/report-settings", response_model=ReportSettingsSchema)
async def get_report_settings(
    ctx: ShopContext = Depends(get_shop_context),
    use_case: GetReportSettingsUseCase = Depends(get_get_report_settings_use_case),
) -> ReportSettingsSchema:
    return ReportSettingsSchema.of(await use_case.get_report_settings(GetReportSettingsQuery(ctx=ctx)))
