from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from zoneinfo import ZoneInfo

from customer.app.dtos.consent_view_dto import FormPetView, SentFormView
from customer.app.dtos.list_forms_dto import ListFormsQuery
from customer.app.ports.input.list_forms_use_case import ListFormsUseCase
from customer.app.ports.output.consent_form_repository import ConsentFormRepository
from customer.app.ports.output.customer_repository import CustomerRepository
from customer.app.ports.output.pet_repository import PetRepository
from customer.app.services.consent_forms import form_url


class ListFormsInteractor(ListFormsUseCase):
    """보낸 서류 — 살아 있는 요청. 잘못 보낸 링크를 여기서 끊는다(⑪ 설계 3.6)."""

    def __init__(
        self, forms: ConsentFormRepository, customers: CustomerRepository, pets: PetRepository,
        now: Callable[[], datetime], link_key: bytes, web_base_url: str,
    ) -> None:
        self._forms = forms
        self._customers = customers
        self._pets = pets
        self._now = now
        self._link_key = link_key
        self._web_base_url = web_base_url

    async def list_forms(self, query: ListFormsQuery) -> list[SentFormView]:
        ctx = query.ctx
        forms = await self._forms.list_live(ctx, self._now())
        if not forms:
            return []
        owners = sorted({form.customer_id for form in forms})
        names = {c.id: c.name for c in await self._customers.list_active(ctx, owners)}
        pets = {p.id: p.name for p in await self._pets.list_for_customers(ctx, owners)}
        zone = ZoneInfo(ctx.timezone)
        return [
            SentFormView(
                form_id=form.id, kind="consent", customer_id=form.customer_id,
                customer_name=names[form.customer_id],
                pets=tuple(FormPetView(pet_id, pets[pet_id]) for pet_id in form.pet_ids if pet_id in pets),
                sent_on=form.created_at.astimezone(zone).date(), expires_on=form.expires_at.astimezone(zone).date(),
                url=form_url(form, link_key=self._link_key, web_base_url=self._web_base_url),
            )
            for form in forms
            if form.customer_id in names     # 익명화한 고객의 요청은 그때 끊겼다 — 남아 있어도 보이지 않는다
        ]
