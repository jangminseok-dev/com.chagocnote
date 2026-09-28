from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.schemas.get_report_settings_schema import ReportSettingsSchema
from visit.adapter.inbound.api.schemas.update_report_settings_schema import (
    UpdateReportSettingsRequestSchema,
)
from visit.app.dtos.update_report_settings_dto import UpdateReportSettingsCommand
from visit.app.ports.input.update_report_settings_use_case import UpdateReportSettingsUseCase
from visit.dependencies.update_report_settings_provider import get_update_report_settings_use_case

update_report_settings_router = APIRouter(prefix="/v1/shops", tags=["visits"])


@update_report_settings_router.put("/{shop_id}/report-settings", response_model=ReportSettingsSchema)
async def update_report_settings(
    body: UpdateReportSettingsRequestSchema,
    ctx: ShopContext = Depends(require_permission("shop:update")),
    use_case: UpdateReportSettingsUseCase = Depends(get_update_report_settings_use_case),
) -> ReportSettingsSchema:
    settings = await use_case.update_report_settings(
        UpdateReportSettingsCommand(ctx=ctx, settings=body.to_settings())
    )
    return ReportSettingsSchema.of(settings)
