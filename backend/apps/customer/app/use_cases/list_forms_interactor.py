from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from zoneinfo import ZoneInfo

from customer.app.dtos.consent_view_dto import FormPetView, SentFormView
from customer.app.dtos.list_forms_dto import ListFormsQuery
from customer.app.ports.input.list_forms_use_case import ListFormsUseCase
from customer.app.ports.output.consent_form_repository import ConsentFormRepository
from customer.app.ports.output.intake_form_repository import IntakeFormRepository
from customer.app.ports.output.customer_repository import CustomerRepository
from customer.app.ports.output.pet_repository import PetRepository
from customer.app.services.consent_forms import form_url


class ListFormsInteractor(ListFormsUseCase):
    """보낸 서류 — 살아 있는 요청(동의서와 문진표), 보낸 날 내림차순. 잘못 보낸 링크를 여기서 끊는다(⑪ 설계 3.6)."""

    def __init__(
        self, forms: ConsentFormRepository, customers: CustomerRepository, pets: PetRepository,
        now: Callable[[], datetime], link_key: bytes, web_base_url: str,
        intakes: IntakeFormRepository | None = None,
    ) -> None:
        self._forms = forms
        self._intakes = intakes      # 문진표 요청(⑪-C) — 주지 않으면 동의서만 싣는다
        self._customers = customers
        self._pets = pets
        self._now = now
        self._link_key = link_key
        self._web_base_url = web_base_url

    async def list_forms(self, query: ListFormsQuery) -> list[SentFormView]:
        ctx, now = query.ctx, self._now()
        consents = await self._forms.list_live(ctx, now)
        intakes = [] if self._intakes is None else await self._intakes.list_live(ctx, now)
        if not consents and not intakes:
            return []
        owners = sorted({form.customer_id for form in [*consents, *intakes] if form.customer_id is not None})
        names = {c.id: c.name for c in await self._customers.list_active(ctx, owners)} if owners else {}
        pets = {p.id: p.name for p in await self._pets.list_for_customers(ctx, owners)} if owners else {}
        zone = ZoneInfo(ctx.timezone)

        def view(form, kind: str, pet_ids, mode: str | None) -> SentFormView:
            return SentFormView(
                form_id=form.id, kind=kind, customer_id=form.customer_id,
                customer_name=names.get(form.customer_id),
                pets=tuple(FormPetView(pet_id, pets[pet_id]) for pet_id in pet_ids if pet_id in pets),
                sent_on=form.created_at.astimezone(zone).date(), expires_on=form.expires_at.astimezone(zone).date(),
                url=form_url(form, link_key=self._link_key, web_base_url=self._web_base_url), mode=mode,
            )

        found = [
            (form.created_at, form.id, view(form, "consent", form.pet_ids, None))
            for form in consents
            if form.customer_id in names     # 익명화한 고객의 요청은 그때 끊겼다 — 남아 있어도 보이지 않는다
        ] + [
            (form.created_at, form.id, view(form, "intake", () if form.pet_id is None else (form.pet_id,), form.mode))
            for form in intakes
            if form.customer_id is None or form.customer_id in names
        ]
        return [item for _, _, item in sorted(found, key=lambda entry: entry[:2], reverse=True)]
