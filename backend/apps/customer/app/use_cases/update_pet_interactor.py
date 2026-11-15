from __future__ import annotations

from collections.abc import Callable
from datetime import date

from customer.app.dtos.customer_view_dto import PetDetailView
from customer.app.dtos.update_pet_dto import UpdatePetCommand
from customer.app.ports.input.update_pet_use_case import UpdatePetUseCase
from customer.app.ports.output.condition_type_repository import ConditionTypeRepository
from customer.app.ports.output.customer_repository import CustomerRepository
from customer.app.ports.output.customer_search_port import CustomerSearchPort
from customer.app.ports.output.pet_repository import PetRepository
from customer.app.services.detail_reader import read_pet_detail
from customer.domain.services.care_marks import conditions_added
from hub.app.dtos.search_events import SearchSourceChanged
from hub.app.ports.domain_event_port import DomainEventPort


class UpdatePetInteractor(UpdatePetUseCase):
    def __init__(
        self, customers: CustomerRepository, pets: PetRepository,
        condition_types: ConditionTypeRepository, search: CustomerSearchPort,
        today: Callable[[], date], events: DomainEventPort,
    ) -> None:
        self._customers = customers
        self._pets = pets
        self._condition_types = condition_types
        self._search = search
        self._today = today
        self._events = events

    async def update_pet(self, command: UpdatePetCommand) -> PetDetailView:
        codes = frozenset(t.code for t in await self._condition_types.list_all())
        profile = command.pet.to_profile(codes, self._today())
        customer_id = await self._pets.lock_owner(command.ctx, command.pet_id)
        before = await self._pets.get(command.ctx, command.pet_id)
        await self._pets.update(command.ctx, command.pet_id, profile)
        # 앞서 받은 미용 동의는 새로 적힌 지병을 덮지 않는다 — 지병이 늘면 다시 받게 한다(③-B 3.2).
        # 서명으로 받은 동의는 지우지 않는다 — 서명에 그때 보인 지병이 남아 있어 바뀐 토막만 다시 받는다(⑪ 3.3).
        if (before.grooming_consent_on is not None and before.grooming_consent_signature_id is None
                and conditions_added(before.conditions, profile.conditions)):
            await self._pets.set_grooming_consent(command.ctx, command.pet_id, None, None)
        await self._search.rebuild_search_entry(command.ctx, customer_id)
        # 특이사항·지병이 기록 검색에 든다(⑨).
        await self._events.publish(SearchSourceChanged(ctx=command.ctx, scope="pet", ref_id=command.pet_id))
        return await read_pet_detail(
            command.ctx, command.pet_id, self._customers, self._pets, self._today()
        )
