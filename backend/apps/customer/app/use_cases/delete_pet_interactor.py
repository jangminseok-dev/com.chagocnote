from __future__ import annotations

from customer.app.dtos.delete_pet_dto import DeletePetCommand
from customer.app.ports.input.delete_pet_use_case import DeletePetUseCase
from customer.app.ports.output.customer_search_port import CustomerSearchPort
from customer.app.ports.output.pet_repository import PetRepository
from customer.domain.errors import LastPetError, PetHasVisitsError
from hub.app.ports.visit_ledger_port import VisitLedgerPort


class DeletePetInteractor(DeletePetUseCase):
    """잘못 등록한 반려동물을 지운다. 세상을 떠난 아이는 지우지 않고 무지개다리로 둔다."""

    def __init__(self, pets: PetRepository, search: CustomerSearchPort, ledger: VisitLedgerPort) -> None:
        self._pets = pets
        self._search = search
        self._ledger = ledger

    async def delete_pet(self, command: DeletePetCommand) -> None:
        # 고객 행을 잠근 뒤 센다. 잠금이 없으면 마지막 두 마리를 동시에 지워 반려동물 없는 가족이 남는다.
        customer_id = await self._pets.lock_owner(command.ctx, command.pet_id)
        # 고객 행을 쥔 뒤에 묻는다 — 예약 등록도 같은 고객 행을 먼저 잠그므로 그 사이 방문이 생기지 않는다.
        if await self._ledger.pet_has_visits(command.ctx, command.pet_id):
            raise PetHasVisitsError("방문 기록이 있는 반려동물은 지울 수 없습니다. 무지개다리를 이용해 주세요.")
        if await self._pets.count_for_customer(command.ctx, customer_id) <= 1:
            raise LastPetError("마지막 반려동물은 지울 수 없습니다. 고객 삭제를 이용해 주세요.")
        await self._pets.delete(command.ctx, command.pet_id)
        await self._search.rebuild_search_entry(command.ctx, customer_id)
