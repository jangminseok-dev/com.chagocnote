from __future__ import annotations

from customer.app.dtos.delete_customer_dto import DeleteCustomerCommand
from customer.app.ports.input.delete_customer_use_case import DeleteCustomerUseCase
from customer.app.ports.output.customer_repository import CustomerRepository
from customer.app.ports.output.customer_search_port import CustomerSearchPort


class DeleteCustomerInteractor(DeleteCustomerUseCase):
    """고객 삭제는 익명화다. 개인정보만 지우고 행은 남긴다(③·④의 기록이 가리킬 틀)."""

    def __init__(self, customers: CustomerRepository, search: CustomerSearchPort) -> None:
        self._customers = customers
        self._search = search

    async def delete_customer(self, command: DeleteCustomerCommand) -> None:
        await self._customers.lock_active(command.ctx, command.customer_id)
        await self._customers.anonymize(command.ctx, command.customer_id)
        await self._search.rebuild_search_entry(command.ctx, command.customer_id)   # 익명화한 고객이라 줄이 지워진다
