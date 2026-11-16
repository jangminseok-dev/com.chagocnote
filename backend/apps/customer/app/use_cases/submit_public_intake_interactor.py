from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from zoneinfo import ZoneInfo

from customer.app.dtos.public_form_dto import SubmitPublicIntakeCommand
from customer.app.ports.input.submit_public_intake_use_case import SubmitPublicIntakeUseCase
from customer.app.ports.output.customer_repository import CustomerRepository
from customer.app.ports.output.intake_answer_repository import IntakeAnswerRepository
from customer.app.ports.output.intake_form_repository import IntakeFormRepository
from customer.app.services.intake_reader import IntakeReader
from customer.app.services.public_form_gate import open_form
from customer.domain.entities.intake import ANSWERS_PER_FORM, NEW, UPDATE
from customer.domain.errors import CustomerNotFoundError, FormClosedError
from customer.domain.services.intake_rules import clean_entry
from dataclasses import replace
from hub.app.dtos.shop_context import public_context
from hub.app.ports.public_limiter_port import PublicLimiterPort
from hub.app.ports.shop_profile_port import ShopProfilePort


class SubmitPublicIntakeInteractor(SubmitPublicIntakeUseCase):
    """보호자가 로그인 없이 문진표를 낸다(⑪ 설계 3.4). 낸 것은 "받은 문진표"다 — 고객·반려동물 표를 건드리지 않는다.

    한 링크에 아이 한 마리씩, 열 마리까지. 다시 받기는 한 번 내면 닫히고, 그 밖에는 `done`(다 적었어요)이나
    열 마리째에서 닫힌다. 번호가 같은 고객이 있으면 미리 이어 둔다 — 반영은 사장이 누른다.
    잠금: (고객이 있으면) 고객 행 → 서류 요청 행.
    """

    def __init__(
        self, forms: IntakeFormRepository, answers: IntakeAnswerRepository, customers: CustomerRepository,
        reader: IntakeReader, shops: ShopProfilePort, limiter: PublicLimiterPort, now: Callable[[], datetime],
        link_key: bytes,
    ) -> None:
        self._forms = forms
        self._answers = answers
        self._customers = customers
        self._reader = reader
        self._shops = shops
        self._limiter = limiter
        self._now = now
        self._link_key = link_key

    async def submit_public_intake(self, command: SubmitPublicIntakeCommand) -> None:
        now = self._now()
        # 문진표 요청만 찾는다 — 동의서 토큰은 여기서 404 다.
        found, shop = await open_form(
            command.token, command.client, now, link_key=self._link_key, forms=self._forms, shops=self._shops,
            limiter=self._limiter,
        )
        ctx = public_context(shop)
        if found.customer_id is not None:
            try:
                await self._customers.lock_active(ctx, found.customer_id)
            except CustomerNotFoundError:
                raise FormClosedError("닫힌 서류입니다.") from None
        form = await self._forms.lock(found.id)
        # 잠금을 기다리는 사이 다 적었거나 끊었을 수 있다 — 잠근 뒤의 값으로 다시 본다.
        if form is None or not form.is_live(now) or form.answered >= ANSWERS_PER_FORM:
            raise FormClosedError("닫힌 서류입니다.")
        layout = await self._reader.layout(ctx)
        guardian = await self._answers.first_guardian(form.id) if form.mode == NEW else None
        answer = clean_entry(
            command.entry, mode=form.mode, hidden=layout.hidden, questions=layout.questions,
            known_codes=frozenset(code for code, _ in layout.condition_types),
            today=now.astimezone(ZoneInfo(ctx.timezone)).date(), first=guardian is None,
        )
        if guardian is not None:
            answer = replace(answer, guardian_name=guardian[0], guardian_phone=guardian[1])   # 둘째 아이 — 같은 보호자다
        matched = form.customer_id
        if form.mode == NEW:
            # 번호가 같은 고객을 미리 찾아 적어 둔다. 잠그지 않는다 — 읽어 둘 뿐이다.
            known = await self._customers.find_active_by_phone(ctx, answer.guardian_phone)
            matched = None if known is None else known.id
        await self._answers.add(ctx, form.id, answer, matched, now)
        if form.mode == UPDATE or command.done or form.answered + 1 >= ANSWERS_PER_FORM:
            await self._forms.mark_submitted(form.id, now)
