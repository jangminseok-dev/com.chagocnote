from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime
from zoneinfo import ZoneInfo

from customer.app.dtos.get_intake_answer_dto import GetIntakeAnswerQuery
from customer.app.dtos.intake_answer_view_dto import IntakeAnswerView, IntakeConsentSummary
from customer.app.ports.input.get_intake_answer_use_case import GetIntakeAnswerUseCase
from customer.app.ports.output.condition_type_repository import ConditionTypeRepository
from customer.app.ports.output.consent_signature_repository import ConsentSignatureRepository
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
        signatures: ConsentSignatureRepository | None = None,
    ) -> None:
        self._answers = answers
        self._settings = settings
        self._customers = customers
        self._pets = pets
        self._condition_types = condition_types
        self._now = now
        self._signatures = signatures

    async def get_intake_answer(self, query: GetIntakeAnswerQuery) -> IntakeAnswerView:
        ctx = query.ctx
        found = await self._answers.get(ctx, query.answer_id, await kept_since(ctx, self._now(), self._settings))
        if found is None:
            raise IntakeAnswerNotFoundError("받은 문진표를 찾을 수 없습니다.")
        (view,) = await describe_answers(
            ctx, [found], customers=self._customers, pets=self._pets, condition_types=self._condition_types)
        if self._signatures is None:
            return view
        held = (await self._signatures.held_for(ctx, [found.id])).get(found.id)
        if held is None:
            return view
        signed_on = held.signed_at.astimezone(ZoneInfo(ctx.timezone)).date()
        return replace(view, consent=IntakeConsentSummary(signed_on=signed_on, parts=held.parts))
