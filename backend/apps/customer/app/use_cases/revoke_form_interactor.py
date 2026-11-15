from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from customer.app.dtos.revoke_form_dto import RevokeFormCommand
from customer.app.ports.input.revoke_form_use_case import RevokeFormUseCase
from customer.app.ports.output.consent_form_repository import ConsentFormRepository
from customer.app.ports.output.customer_repository import CustomerRepository
from customer.domain.errors import CustomerNotFoundError


class RevokeFormInteractor(RevokeFormUseCase):
    """링크를 끊는다. 이미 닫힌 요청도 조용히 끝난다 — 없는 요청만 404 다."""

    def __init__(
        self, forms: ConsentFormRepository, customers: CustomerRepository, now: Callable[[], datetime],
    ) -> None:
        self._forms = forms
        self._customers = customers
        self._now = now

    async def revoke_form(self, command: RevokeFormCommand) -> None:
        form = await self._forms.get(command.ctx, command.form_id)
        try:
            await self._customers.lock_active(command.ctx, form.customer_id)   # 고객 행 → 서류 요청 행
        except CustomerNotFoundError:
            return   # 익명화한 고객의 요청은 그때 이미 끊겼다
        await self._forms.revoke(command.ctx, form.id, self._now())
