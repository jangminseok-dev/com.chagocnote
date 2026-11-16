from __future__ import annotations

from collections.abc import Callable
from datetime import date

from customer.app.dtos.customer_view_dto import CustomerDetailView
from customer.app.dtos.register_customer_dto import RegisterCustomerCommand
from customer.app.ports.input.register_customer_use_case import RegisterCustomerUseCase
from customer.app.ports.output.condition_type_repository import ConditionTypeRepository
from customer.app.ports.output.customer_repository import CustomerRepository
from customer.app.ports.output.customer_search_port import CustomerSearchPort
from customer.app.ports.output.pet_repository import PetRepository
from customer.app.services.detail_reader import read_customer_detail
from customer.app.services.intake_answers import IntakeAnswerUse
from hub.app.dtos.search_events import SearchSourceChanged
from hub.app.ports.domain_event_port import DomainEventPort


class RegisterCustomerInteractor(RegisterCustomerUseCase):
    def __init__(
        self, customers: CustomerRepository, pets: PetRepository,
        condition_types: ConditionTypeRepository, search: CustomerSearchPort,
        today: Callable[[], date], events: DomainEventPort, intake: IntakeAnswerUse | None = None,
    ) -> None:
        self._customers = customers
        self._pets = pets
        self._condition_types = condition_types
        self._search = search
        self._today = today
        self._events = events
        self._intake = intake        # 받은 문진표(⑪-C) — 그 답으로 등록하면 같은 트랜잭션에서 서명을 옮기고 답을 지운다

    async def register_customer(self, command: RegisterCustomerCommand) -> CustomerDetailView:
        # 쓰기 전에 두 폼을 모두 검증한다. 번호 중복은 유일 색인이 막는다(동시에 두 번 와도 하나만 성공).
        codes = frozenset(t.code for t in await self._condition_types.list_all())
        customer_profile = command.customer.to_profile()
        pet_profile = command.pet.to_profile(codes, self._today())
        # 답이 없으면(이미 등록했거나 지웠다) 등록하지 않는다. 뒤에서 실패하면 지운 것도 함께 되돌아간다.
        if self._intake is not None:
            await self._intake.check(command.ctx, command.intake_answer_id)
        customer = await self._customers.create(command.ctx, customer_profile)
        pet = await self._pets.add(command.ctx, customer.id, pet_profile)
        if self._intake is not None:
            await self._intake.finish(
                command.ctx, command.intake_answer_id, customer_id=customer.id, pet_id=pet.id, today=self._today())
        await self._search.rebuild_search_entry(command.ctx, customer.id)
        # 보호자 메모와 아이의 특이사항·지병이 기록 검색에 든다(⑨) — 다시 색인할 줄을 같은 트랜잭션에 넣게 한다.
        await self._events.publish(SearchSourceChanged(ctx=command.ctx, scope="customer", ref_id=customer.id))
        await self._events.publish(SearchSourceChanged(ctx=command.ctx, scope="pet", ref_id=pet.id))
        return await read_customer_detail(
            command.ctx, customer.id, self._customers, self._pets, self._today()
        )
