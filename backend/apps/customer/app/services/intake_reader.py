"""문진표의 지금 구성 — 켜진 칸, 매장이 더한 질문, 지병 종류(⑪ 설계 3.4). 공개 읽기와 제출이 함께 쓴다."""
from __future__ import annotations

from dataclasses import dataclass

from customer.app.dtos.public_form_dto import PublicIntakeView
from customer.app.ports.output.condition_type_repository import ConditionTypeRepository
from customer.app.ports.output.form_settings_repository import FormSettingsRepository
from customer.app.ports.output.intake_answer_repository import IntakeAnswerRepository
from customer.app.ports.output.intake_question_repository import IntakeQuestionRepository
from customer.app.ports.output.pet_repository import PetRepository
from customer.domain.entities.intake import NEW, IntakeForm, IntakeQuestion
from customer.domain.errors import FormClosedError, PetNotFoundError
from customer.domain.services.form_settings_rules import INTAKE_HIDEABLE
from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class IntakeLayout:
    hidden: frozenset[str]
    keep_days: int
    questions: list[IntakeQuestion]
    condition_types: tuple[tuple[str, str], ...]


class IntakeReader:
    def __init__(
        self, settings: FormSettingsRepository, questions: IntakeQuestionRepository,
        condition_types: ConditionTypeRepository, pets: PetRepository, answers: IntakeAnswerRepository,
    ) -> None:
        self._settings = settings
        self._questions = questions
        self._condition_types = condition_types
        self._pets = pets
        self._answers = answers

    async def layout(self, ctx: ShopContext) -> IntakeLayout:
        """열 때마다 다시 읽는다 — 보낸 뒤 매장이 칸을 끄거나 질문을 고쳤으면 새 구성이다."""
        settings = await self._settings.get(ctx)
        return IntakeLayout(
            hidden=frozenset(settings.intake_hidden), keep_days=settings.intake_keep_days,
            questions=await self._questions.list_live(ctx),
            condition_types=tuple((t.code, t.label) for t in await self._condition_types.list_all()),
        )

    async def read(self, ctx: ShopContext, form: IntakeForm) -> PublicIntakeView:
        layout = await self.layout(ctx)
        pet_name = None
        if form.pet_id is not None:
            try:
                pet = await self._pets.get(ctx, form.pet_id)
            except PetNotFoundError:
                raise FormClosedError("닫힌 서류입니다.") from None
            if pet.passed_away:
                raise FormClosedError("닫힌 서류입니다.")
            pet_name = pet.name
        return PublicIntakeView(
            mode=form.mode, pet_name=pet_name,
            fields=tuple(code for code in INTAKE_HIDEABLE if code not in layout.hidden),
            questions=tuple(layout.questions), condition_types=layout.condition_types, answered=form.answered,
            # 제출이 쓰는 규칙과 같다 — 새 손님의 답 가운데 보호자를 적은 것이 남아 있지 않으면 묻는다.
            keep_days=layout.keep_days,
            guardian_needed=form.mode == NEW and await self._answers.first_guardian(form.id) is None,
        )
