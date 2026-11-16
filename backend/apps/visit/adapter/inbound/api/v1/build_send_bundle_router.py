from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.path_params import VisitId
from visit.adapter.inbound.api.schemas.build_send_bundle_schema import SendBundleSchema
from visit.app.dtos.build_send_bundle_dto import BuildSendBundleCommand
from visit.app.ports.input.build_send_bundle_use_case import BuildSendBundleUseCase
from visit.dependencies.build_send_bundle_provider import get_build_send_bundle_use_case

build_send_bundle_router = APIRouter(prefix="/v1/shops", tags=["visits"])


# 읽기처럼 보이지만 동의서 링크가 없으면 이때 만든다 — 그래서 POST 다. 응답의 주소를 로그에 남기지 않는다.
@build_send_bundle_router.post("/{shop_id}/visits/{visit_id}/send-bundle", response_model=SendBundleSchema)
async def build_send_bundle(
    visit_id: VisitId,
    ctx: ShopContext = Depends(require_permission("reservation:write")),
    use_case: BuildSendBundleUseCase = Depends(get_build_send_bundle_use_case),
) -> SendBundleSchema:
    return SendBundleSchema.of(await use_case.build_send_bundle(BuildSendBundleCommand(ctx=ctx, visit_id=visit_id)))
