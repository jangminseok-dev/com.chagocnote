from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from core.link_token import new_public_id
from customer.app.dtos.consent_view_dto import FormLinkView
from customer.app.dtos.issue_intake_form_dto import IssueIntakeFormCommand
from customer.app.ports.input.issue_intake_form_use_case import IssueIntakeFormUseCase
from customer.app.ports.output.customer_repository import CustomerRepository
from customer.app.ports.output.form_settings_repository import FormSettingsRepository
from customer.app.ports.output.intake_form_repository import IntakeFormRepository
from customer.app.ports.output.pet_repository import PetRepository
from customer.app.services.consent_forms import form_url
from customer.domain.entities.intake import IntakeForm
from customer.domain.errors import CustomerInputError


class IssueIntakeFormInteractor(IssueIntakeFormUseCase):
    """문진표 링크를 보낸다(⑪ 설계 3.4). 고객·반려동물 표를 건드리지 않는다 — 답은 "받은 문진표"로 온다.

    새 아이·다시 받기는 같은 대상의 살아 있는 요청이 있으면 같은 링크다. 새 손님용은 대상이 없어 늘 새 링크다.
    """

    def __init__(
        self, customers: CustomerRepository, pets: PetRepository, forms: IntakeFormRepository,
        settings: FormSettingsRepository, now: Callable[[], datetime], link_key: bytes, web_base_url: str,
    ) -> None:
        self._customers = customers
        self._pets = pets
        self._forms = forms
        self._settings = settings
        self._now = now
        self._link_key = link_key
        self._web_base_url = web_base_url

    async def issue_intake_form(self, command: IssueIntakeFormCommand) -> FormLinkView:
        ctx, now = command.ctx, self._now()
        customer_id, pet_id = command.customer_id, command.pet_id
        # 고객 행을 먼저 잠근다(고객 행 → 서류 요청 행) — 같은 대상에 동시에 보내도 요청이 하나만 생긴다.
        if pet_id is not None:
            owner = await self._pets.lock_owner(ctx, pet_id)
            if customer_id is not None and customer_id != owner:
                raise CustomerInputError("그 고객의 반려동물이 아닙니다.")
            if (await self._pets.get(ctx, pet_id)).passed_away:
                raise CustomerInputError("무지개다리를 건넌 아이에게는 보낼 수 없습니다.")
            customer_id = owner
        elif customer_id is not None:
            await self._customers.lock_active(ctx, customer_id)
        if customer_id is not None:
            # 열지 않은 채 기간이 지난 요청을 먼저 닫는다 — 남아 있으면 그 아이에게 다시 보낼 수 없다.
            await self._forms.close_expired(ctx, customer_id, now)
            same = await self._forms.live_for(ctx, customer_id, pet_id, now)
            if same is not None:
                return self._view(ctx.timezone, same, created=False)
        days = (await self._settings.get(ctx)).link_days
        form = await self._forms.create(ctx, customer_id, pet_id, new_public_id(), now + timedelta(days=days))
        return self._view(ctx.timezone, form, created=True)

    def _view(self, timezone: str, form: IntakeForm, *, created: bool) -> FormLinkView:
        zone = ZoneInfo(timezone)
        return FormLinkView(
            form_id=form.id, url=form_url(form, link_key=self._link_key, web_base_url=self._web_base_url),
            expires_on=form.expires_at.astimezone(zone).date(), sent_on=form.created_at.astimezone(zone).date(),
            created=created,
        )
