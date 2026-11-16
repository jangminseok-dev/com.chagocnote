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
from customer.app.services.consent_source import ConsentSource
from customer.domain.entities.consent_form import ConsentForm
from customer.domain.errors import ConsentUpToDateError, CustomerInputError
from customer.domain.services.consent_document import base_date


class IssueConsentFormInteractor(IssueConsentFormUseCase):
    """동의서 링크를 보낸다(⑪ 설계 3.1). 아이 하나에 살아 있는 요청은 하나다 — 같은 아이들에게 다시 보내면 같은 링크다."""

    def __init__(
        self, pets: PetRepository, signatures: ConsentSignatureRepository, forms: ConsentFormRepository,
        today: Callable[[], date], now: Callable[[], datetime], source: ConsentSource,
        link_key: bytes, web_base_url: str,
    ) -> None:
        self._pets = pets
        self._signatures = signatures
        self._forms = forms
        self._today = today
        self._now = now
        self._source = source
        self._link_key = link_key
        self._web_base_url = web_base_url

    async def issue_consent_form(self, command: IssueConsentFormCommand) -> FormLinkView:
        ctx = command.ctx
        if not command.pet_ids:
            raise CustomerInputError("아이를 하나 이상 골라 주세요.")
        now = self._now()
        # 고객 행을 먼저 잠근다 — 같은 가족에게 동시에 보내도 요청이 하나만 생긴다(고객 행 → 서류 요청 행).
        customer_id = await self._pets.lock_owner(ctx, min(command.pet_ids))
        policy = await self._source.policy(ctx)
        on = base_date(self._today(), command.for_date, policy)
        doc = await read_document(
            ctx, command.pet_ids, on, policy, pets=self._pets, signatures=self._signatures,
            texts=await self._source.texts(ctx))
        if not doc.pets:
            raise ConsentUpToDateError("이미 받은 동의입니다.")
        wanted = tuple(pet.pet_id for pet in doc.pets)
        live = await self._forms.live_for_customer(ctx, customer_id, now)
        # 그 아이들을 모두 담은 살아 있는 요청이 있으면 그것이다 — 가족 링크의 한 아이만 다시 보내도 링크가 쪼개지지 않는다.
        same = next((form for form in live if set(wanted) <= set(form.pet_ids)), None)
        if same is not None:
            # 더 먼 예약 날로 다시 보냈으면 링크의 기준일을 그날로 맞춘다.
            if command.for_date is not None and (same.for_date is None or same.for_date < on):
                await self._forms.set_for_date(ctx, same.id, on)
            return self._view(ctx.timezone, same, created=False)
        await drop_pets(ctx, customer_id, wanted, now, self._forms)
        form = await self._forms.create(
            ctx, customer_id, wanted, new_public_id(), now + timedelta(days=policy.link_days),
            for_date=None if command.for_date is None else on)
        return self._view(ctx.timezone, form, created=True)

    def _view(self, timezone: str, form: ConsentForm, *, created: bool) -> FormLinkView:
        zone = ZoneInfo(timezone)
        return FormLinkView(
            form_id=form.id, url=form_url(form, link_key=self._link_key, web_base_url=self._web_base_url),
            expires_on=form.expires_at.astimezone(zone).date(), sent_on=form.created_at.astimezone(zone).date(),
            created=created,
        )
