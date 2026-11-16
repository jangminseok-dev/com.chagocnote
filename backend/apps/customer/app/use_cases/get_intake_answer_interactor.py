from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from customer.app.dtos.get_intake_answer_dto import GetIntakeAnswerQuery
from customer.app.dtos.intake_answer_view_dto import IntakeAnswerView
from customer.app.ports.input.get_intake_answer_use_case import GetIntakeAnswerUseCase
from customer.app.ports.output.condition_type_repository import ConditionTypeRepository
from customer.app.ports.output.customer_repository import CustomerRepository
from customer.app.ports.output.form_settings_repository import FormSettingsRepository
from customer.app.ports.output.intake_answer_repository import IntakeAnswerRepository
from customer.app.ports.output.pet_repository import PetRepository
from customer.app.services.intake_answers import describe_answers, kept_since
from customer.domain.errors import IntakeAnswerNotFoundError


class GetIntakeAnswerInteractor(GetIntakeAnswerUseCase):
    """받은 문진표 한 장 — 답 전부와, 등록 화면에 옮길 때 쓸 것(빈 필수 칸·메모 초안)."""

    def __init__(
        self, answers: IntakeAnswerRepository, settings: FormSettingsRepository, customers: CustomerRepository,
        pets: PetRepository, condition_types: ConditionTypeRepository, now: Callable[[], datetime],
    ) -> None:
        self._answers = answers
        self._settings = settings
        self._customers = customers
        self._pets = pets
        self._condition_types = condition_types
        self._now = now

    async def get_intake_answer(self, query: GetIntakeAnswerQuery) -> IntakeAnswerView:
        ctx = query.ctx
        found = await self._answers.get(ctx, query.answer_id, await kept_since(ctx, self._now(), self._settings))
        if found is None:
            raise IntakeAnswerNotFoundError("받은 문진표를 찾을 수 없습니다.")
        (view,) = await describe_answers(
            ctx, [found], customers=self._customers, pets=self._pets, condition_types=self._condition_types)
        return view
