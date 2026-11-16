from __future__ import annotations

from collections.abc import Callable
from datetime import date

from customer.app.dtos.add_pet_dto import AddPetCommand
from customer.app.dtos.customer_view_dto import PetDetailView
from customer.app.ports.input.add_pet_use_case import AddPetUseCase
from customer.app.ports.output.condition_type_repository import ConditionTypeRepository
from customer.app.ports.output.customer_repository import CustomerRepository
from customer.app.ports.output.customer_search_port import CustomerSearchPort
from customer.app.ports.output.intake_answer_repository import IntakeAnswerRepository
from customer.app.ports.output.pet_repository import PetRepository
from customer.app.services.intake_answers import consume_answer
from customer.app.services.detail_reader import read_pet_detail
from hub.app.dtos.search_events import SearchSourceChanged
from hub.app.ports.domain_event_port import DomainEventPort


class AddPetInteractor(AddPetUseCase):
    def __init__(
        self, customers: CustomerRepository, pets: PetRepository,
        condition_types: ConditionTypeRepository, search: CustomerSearchPort,
        today: Callable[[], date], events: DomainEventPort, answers: IntakeAnswerRepository | None = None,
    ) -> None:
        self._customers = customers
        self._pets = pets
        self._condition_types = condition_types
        self._search = search
        self._today = today
        self._events = events
        self._answers = answers

    async def add_pet(self, command: AddPetCommand) -> PetDetailView:
        codes = frozenset(t.code for t in await self._condition_types.list_all())
        profile = command.pet.to_profile(codes, self._today())
        # 고객 행을 잠근 뒤 다시 읽는다. 익명화한 고객에게 이름 있는 반려동물을 붙이지 않는다.
        await self._customers.lock_active(command.ctx, command.customer_id)
        await consume_answer(
            command.ctx, command.intake_answer_id, self._answers, customer_id=command.customer_id)   # 받은 문진표로 더한다(⑪-C)
        pet = await self._pets.add(command.ctx, command.customer_id, profile)
        await self._search.rebuild_search_entry(command.ctx, command.customer_id)
        await self._events.publish(SearchSourceChanged(ctx=command.ctx, scope="pet", ref_id=pet.id))   # 기록 검색(⑨)
        return await read_pet_detail(command.ctx, pet.id, self._customers, self._pets, self._today())
