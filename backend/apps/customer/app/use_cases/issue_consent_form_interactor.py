from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from core.link_token import new_public_id
from customer.app.dtos.consent_view_dto import FormLinkView
from customer.app.dtos.issue_consent_form_dto import IssueConsentFormCommand
from customer.app.ports.input.issue_consent_form_use_case import IssueConsentFormUseCase
from customer.app.ports.output.consent_form_repository import ConsentFormRepository
from customer.app.ports.output.consent_signature_repository import ConsentSignatureRepository
from customer.app.ports.output.pet_repository import PetRepository
from customer.app.services.consent_forms import drop_pets, form_url
from customer.app.services.consent_reader import read_document
from customer.domain.entities.consent import ConsentPolicy
from customer.domain.entities.consent_form import ConsentForm
from customer.domain.errors import ConsentUpToDateError, CustomerInputError


class IssueConsentFormInteractor(IssueConsentFormUseCase):
    """동의서 링크를 보낸다(⑪ 설계 3.1). 아이 하나에 살아 있는 요청은 하나다 — 같은 아이들에게 다시 보내면 같은 링크다."""

    def __init__(
        self, pets: PetRepository, signatures: ConsentSignatureRepository, forms: ConsentFormRepository,
        today: Callable[[], date], now: Callable[[], datetime], policy: ConsentPolicy,
        link_key: bytes, web_base_url: str,
    ) -> None:
        self._pets = pets
        self._signatures = signatures
        self._forms = forms
        self._today = today
        self._now = now
        self._policy = policy
        self._link_key = link_key
        self._web_base_url = web_base_url

    async def issue_consent_form(self, command: IssueConsentFormCommand) -> FormLinkView:
        ctx = command.ctx
        if not command.pet_ids:
            raise CustomerInputError("아이를 하나 이상 골라 주세요.")
        now = self._now()
        # 고객 행을 먼저 잠근다 — 같은 가족에게 동시에 보내도 요청이 하나만 생긴다(고객 행 → 서류 요청 행).
        customer_id = await self._pets.lock_owner(ctx, min(command.pet_ids))
        doc = await read_document(
            ctx, command.pet_ids, self._today(), self._policy, pets=self._pets, signatures=self._signatures)
        if not doc.pets:
            raise ConsentUpToDateError("이미 받은 동의입니다.")
        wanted = tuple(pet.pet_id for pet in doc.pets)
        live = await self._forms.live_for_customer(ctx, customer_id, now)
        same = next((form for form in live if form.pet_ids == wanted), None)
        if same is not None:
            return self._view(ctx.timezone, same, created=False)
        await drop_pets(ctx, customer_id, wanted, now, self._forms)
        form = await self._forms.create(
            ctx, customer_id, wanted, new_public_id(), now + timedelta(days=self._policy.link_days))
        return self._view(ctx.timezone, form, created=True)

    def _view(self, timezone: str, form: ConsentForm, *, created: bool) -> FormLinkView:
        zone = ZoneInfo(timezone)
        return FormLinkView(
            form_id=form.id, url=form_url(form, link_key=self._link_key, web_base_url=self._web_base_url),
            expires_on=form.expires_at.astimezone(zone).date(), sent_on=form.created_at.astimezone(zone).date(),
            created=created,
        )
