from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from customer.app.dtos.intake_answer_view_dto import IntakeAnswerView
from customer.app.dtos.list_intake_answers_dto import ListIntakeAnswersQuery
from customer.app.ports.input.list_intake_answers_use_case import ListIntakeAnswersUseCase
from customer.app.ports.output.condition_type_repository import ConditionTypeRepository
from customer.app.ports.output.customer_repository import CustomerRepository
from customer.app.ports.output.form_settings_repository import FormSettingsRepository
from customer.app.ports.output.intake_answer_repository import IntakeAnswerRepository
from customer.app.ports.output.pet_repository import PetRepository
from customer.app.services.intake_answers import describe_answers, kept_since


class ListIntakeAnswersInteractor(ListIntakeAnswersUseCase):
    """받은 문진표 — 아직 등록하지 않은 답, 받은 시각 내림차순. 보관 기간이 지난 답은 없는 것으로 친다."""

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

    async def list_intake_answers(self, query: ListIntakeAnswersQuery) -> list[IntakeAnswerView]:
        ctx = query.ctx
        found = await self._answers.list_since(ctx, await kept_since(ctx, self._now(), self._settings))
        return await describe_answers(
            ctx, found, customers=self._customers, pets=self._pets, condition_types=self._condition_types)
