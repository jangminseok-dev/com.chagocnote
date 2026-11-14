from __future__ import annotations

from collections.abc import Callable
from datetime import date

from customer.app.dtos.customer_view_dto import CustomerDetailView
from customer.app.dtos.set_customer_caution_dto import SetCustomerCautionCommand
from customer.app.ports.input.set_customer_caution_use_case import SetCustomerCautionUseCase
from customer.app.ports.output.customer_repository import CustomerRepository
from customer.app.ports.output.pet_repository import PetRepository
from customer.app.services.detail_reader import read_customer_detail
from customer.domain.services.care_marks import caution_until, clean_reason


class SetCustomerCautionInteractor(SetCustomerCautionUseCase):
    """보호자에게 주의 표시를 단다(③-B 3.3). 달거나 고치면 끝나는 날은 오늘로부터 365일 뒤다. 이 매장 안에서만 보인다."""

    def __init__(
        self, customers: CustomerRepository, pets: PetRepository, today: Callable[[], date]
    ) -> None:
        self._customers = customers
        self._pets = pets
        self._today = today

    async def set_customer_caution(self, command: SetCustomerCautionCommand) -> CustomerDetailView:
        reason = clean_reason(command.reason)
        today = self._today()
        await self._customers.lock_active(command.ctx, command.customer_id)
        await self._customers.set_caution(
            command.ctx, command.customer_id, reason, caution_until(today), command.ctx.member_id
        )
        return await read_customer_detail(
            command.ctx, command.customer_id, self._customers, self._pets, today
        )
