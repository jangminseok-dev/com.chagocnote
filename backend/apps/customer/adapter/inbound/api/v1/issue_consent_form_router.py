from fastapi import APIRouter, Depends, Response

from core.shop_guard import require_permission
from customer.adapter.inbound.api.schemas.consent_schema import FormLinkSchema, IssueConsentFormRequestSchema
from customer.app.dtos.issue_consent_form_dto import IssueConsentFormCommand
from customer.app.ports.input.issue_consent_form_use_case import IssueConsentFormUseCase
from customer.dependencies.issue_consent_form_provider import get_issue_consent_form_use_case
from hub.app.dtos.shop_context import ShopContext

issue_consent_form_router = APIRouter(prefix="/v1/shops", tags=["forms"])


# 살아 있는 요청이 있으면 그것을 200 으로 돌려준다(같은 링크). 새로 만들었으면 201.
@issue_consent_form_router.post("/{shop_id}/consent-forms", response_model=FormLinkSchema, status_code=201)
async def issue_consent_form(
    body: IssueConsentFormRequestSchema,
    response: Response,
    ctx: ShopContext = Depends(require_permission("customer:write")),
    use_case: IssueConsentFormUseCase = Depends(get_issue_consent_form_use_case),
) -> FormLinkSchema:
    view = await use_case.issue_consent_form(IssueConsentFormCommand(ctx=ctx, pet_ids=tuple(body.pet_ids)))
    if not view.created:
        response.status_code = 200
    return FormLinkSchema.of(view)
