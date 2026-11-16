"""매장이 정하는 가족 수(⑫ 8절). 보기는 매장 멤버, 바꾸기는 사장(shop:update — 알림장 설정과 같다)."""
from fastapi import APIRouter, Depends

from core.shop_guard import get_shop_context, require_permission
from guardian.adapter.inbound.api.schemas.guardian_family_schema import (
    GuardianSettingsDefaultsSchema, GuardianSettingsSchema, UpdateGuardianSettingsRequestSchema,
)
from guardian.app.dtos.family_dto import GetGuardianSettingsQuery, GuardianSettingsView, UpdateGuardianSettingsCommand
from guardian.app.ports.input.get_guardian_settings_use_case import GetGuardianSettingsUseCase
from guardian.app.ports.input.update_guardian_settings_use_case import UpdateGuardianSettingsUseCase
from guardian.dependencies.family_providers import (
    get_get_guardian_settings_use_case, get_update_guardian_settings_use_case,
)
from hub.app.dtos.shop_context import ShopContext

guardian_settings_router = APIRouter(prefix="/v1/shops", tags=["guardian"])


def _schema(view: GuardianSettingsView) -> GuardianSettingsSchema:
    return GuardianSettingsSchema(
        family_max=view.family_max, defaults=GuardianSettingsDefaultsSchema(family_max=view.default_family_max))


@guardian_settings_router.get("/{shop_id}/guardian-settings", response_model=GuardianSettingsSchema)
async def get_guardian_settings(
    ctx: ShopContext = Depends(get_shop_context),
    use_case: GetGuardianSettingsUseCase = Depends(get_get_guardian_settings_use_case),
) -> GuardianSettingsSchema:
    return _schema(await use_case.get_settings(GetGuardianSettingsQuery(ctx=ctx)))


@guardian_settings_router.put("/{shop_id}/guardian-settings", response_model=GuardianSettingsSchema)
async def update_guardian_settings(
    body: UpdateGuardianSettingsRequestSchema,
    ctx: ShopContext = Depends(require_permission("shop:update")),
    use_case: UpdateGuardianSettingsUseCase = Depends(get_update_guardian_settings_use_case),
) -> GuardianSettingsSchema:
    return _schema(await use_case.update_settings(UpdateGuardianSettingsCommand(ctx=ctx, family_max=body.family_max)))
