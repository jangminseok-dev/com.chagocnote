from __future__ import annotations

from customer.app.dtos.delete_customer_dto import DeleteCustomerCommand
from customer.app.ports.input.delete_customer_use_case import DeleteCustomerUseCase
from customer.app.ports.output.customer_repository import CustomerRepository
from customer.app.ports.output.customer_search_port import CustomerSearchPort
from customer.domain.errors import CustomerHasUpcomingVisitsError
from hub.app.ports.visit_ledger_port import VisitLedgerPort


class DeleteCustomerInteractor(DeleteCustomerUseCase):
    """고객 삭제는 익명화다. 개인정보만 지우고 행은 남긴다(③·④의 기록이 가리킬 틀)."""

    def __init__(
        self, customers: CustomerRepository, search: CustomerSearchPort, ledger: VisitLedgerPort
    ) -> None:
        self._customers = customers
        self._search = search
        self._ledger = ledger

    async def delete_customer(self, command: DeleteCustomerCommand) -> None:
        await self._customers.lock_active(command.ctx, command.customer_id)
        if await self._ledger.customer_has_upcoming(command.ctx, command.customer_id):
            raise CustomerHasUpcomingVisitsError("앞으로의 예약이 남아 있습니다. 예약을 먼저 취소해 주세요.")
        await self._customers.anonymize(command.ctx, command.customer_id)
        await self._ledger.clear_customer_memos(command.ctx, command.customer_id)   # 방문 메모의 개인정보(V11)
        await self._search.rebuild_search_entry(command.ctx, command.customer_id)   # 익명화한 고객이라 줄이 지워진다
