from __future__ import annotations

from datetime import date

from customer.app.dtos.issue_consent_form_dto import IssueConsentFormCommand
from customer.app.ports.input.issue_consent_form_use_case import IssueConsentFormUseCase
from customer.app.ports.output.form_settings_repository import FormSettingsRepository
from customer.domain.errors import ConsentUpToDateError, CustomerInputError, PetNotFoundError
from customer.domain.services.form_settings_rules import DEFAULT_CONSENT_TEXT, DEFAULT_RESERVATION_TEXT
from hub.app.dtos.bundle_texts import BundleTexts, ConsentLink
from hub.app.dtos.shop_context import ShopContext
from hub.app.ports.guardian_form_port import GuardianFormPort


class GuardianFormInteractor(GuardianFormPort):
    """허브의 GuardianFormPort 구현. 입력 포트가 곧 허브 포트다(HTTP 표면 없음).

    링크는 동의서 보내기(issue_consent_form)와 같은 길로 만든다 — 같은 잠금, 같은 "살아 있으면 같은 링크".
    """

    def __init__(self, issue: IssueConsentFormUseCase, settings: FormSettingsRepository) -> None:
        self._issue = issue
        self._settings = settings

    async def consent_link(self, ctx: ShopContext, pet_ids: tuple[int, ...], for_date: date) -> ConsentLink | None:
        if not pet_ids:
            return None
        try:
            view = await self._issue.issue_consent_form(
                IssueConsentFormCommand(ctx=ctx, pet_ids=pet_ids, for_date=for_date))
        except (ConsentUpToDateError, PetNotFoundError, CustomerInputError):
            # 더 받을 것이 없거나 보낼 수 없는 아이다 — 묶음에 동의서 토막이 없을 뿐이다.
            return None
        return ConsentLink(url=view.url, form_id=view.form_id, created=view.created)

    async def bundle_texts(self, ctx: ShopContext) -> BundleTexts:
        settings = await self._settings.get(ctx)
        return BundleTexts(
            reservation=settings.reservation_text or DEFAULT_RESERVATION_TEXT,
            consent=settings.consent_text or DEFAULT_CONSENT_TEXT,
        )
