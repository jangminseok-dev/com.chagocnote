from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import date, datetime
from zoneinfo import ZoneInfo

from customer.app.dtos.public_form_dto import IntakeConsentEntry, SubmitPublicIntakeCommand
from customer.app.ports.input.submit_public_intake_use_case import SubmitPublicIntakeUseCase
from customer.app.ports.output.consent_signature_repository import ConsentSignatureRepository
from customer.app.ports.output.customer_repository import CustomerRepository
from customer.app.ports.output.intake_answer_repository import IntakeAnswerRepository
from customer.app.ports.output.intake_form_repository import IntakeFormRepository
from customer.app.services.consent_signer import SIGNER_NAME_MAX
from customer.app.services.intake_reader import IntakeLayout, IntakeReader, consent_for_all
from customer.app.services.public_form_gate import open_form
from customer.domain.entities.consent_form import NewSignature, NewSignaturePet, SignedPart
from customer.domain.entities.intake import ANSWERS_PER_FORM, NEW, UPDATE, IntakeForm
from customer.domain.errors import (
    ConsentDocumentChangedError, ConsentRequiredError, CustomerInputError, CustomerNotFoundError, FormClosedError,
)
from customer.domain.services.consent_text import PARTS
from customer.domain.services.intake_consent import consent_parts, shown_conditions
from customer.domain.services.intake_rules import CleanAnswer, clean_entry
from customer.domain.services.signature_image import check_png
from hub.app.dtos.shop_context import ShopContext, public_context
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
        link_key: bytes, signatures: ConsentSignatureRepository | None = None,
    ) -> None:
        self._forms = forms
        self._answers = answers
        self._customers = customers
        self._reader = reader
        self._shops = shops
        self._limiter = limiter
        self._now = now
        self._link_key = link_key
        self._signatures = signatures      # 끝의 동의서 구역에서 한 서명을 맡아 둔다(⑪-C1b)

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
        today = now.astimezone(ZoneInfo(ctx.timezone)).date()
        guardian = await self._answers.first_guardian(form.id) if form.mode == NEW else None
        answer = clean_entry(
            command.entry, mode=form.mode, hidden=layout.hidden, questions=layout.questions,
            known_codes=frozenset(code for code, _ in layout.condition_types),
            today=today, first=guardian is None,
        )
        # 동의서 구역(⑪-C1b) — 답을 쓰기 전에 본다. 받지 않으면 답도 남지 않는다.
        signing = self._check_consent(
            command.consent, answer, layout, today, for_all=consent_for_all(layout.consent_all, form.mode))
        if guardian is not None:
            answer = replace(answer, guardian_name=guardian[0], guardian_phone=guardian[1])   # 둘째 아이 — 같은 보호자다
        matched = form.customer_id
        if form.mode == NEW:
            # 번호가 같은 고객을 미리 찾아 적어 둔다. 잠그지 않는다 — 읽어 둘 뿐이다.
            known = await self._customers.find_active_by_phone(ctx, answer.guardian_phone)
            matched = None if known is None else known.id
        answer_id = await self._answers.add(ctx, form.id, answer, matched, now)
        if signing is not None:
            await self._hold_signature(ctx, form, answer, answer_id, signing, layout, now)
        if form.mode == UPDATE or command.done or form.answered + 1 >= ANSWERS_PER_FORM:
            await self._forms.mark_submitted(form.id, now)

    @staticmethod
    def _check_consent(
        consent: IntakeConsentEntry | None, answer: CleanAnswer, layout: IntakeLayout, today: date, *, for_all: bool,
    ) -> IntakeConsentEntry | None:
        """받을 서명을 돌려준다(없으면 None). 연 뒤 매장의 글·기준이 바뀌었으면 409, 필요한데 없으면 422.

        노령도 지병도 아닌데 서명해 보냈으면 받는다 — 보호자가 읽은 토막 그대로 남긴다.
        """
        if consent is not None and consent.digest != layout.consent_digest:
            raise ConsentDocumentChangedError("동의서의 내용이 바뀌었습니다. 다시 읽어 주세요.")
        needed = consent_parts(answer, on=today, policy=layout.policy, for_all=for_all)
        if needed and (consent is None or not set(needed) <= set(consent.parts)):
            raise ConsentRequiredError("동의서에 서명해 주세요.")
        if consent is None:
            return None
        if "basic" not in consent.parts:
            raise ConsentRequiredError("동의서에 서명해 주세요.")
        name = consent.signer_name.strip()
        if not 1 <= len(name) <= SIGNER_NAME_MAX:
            raise CustomerInputError("이름은 1자에서 50자 사이로 적어 주세요.")
        check_png(consent.signature_png)
        return replace(consent, signer_name=name)

    async def _hold_signature(
        self, ctx: ShopContext, form: IntakeForm, answer: CleanAnswer, answer_id: int, consent: IntakeConsentEntry,
        layout: IntakeLayout, now: datetime,
    ) -> None:
        """서명을 아이 없이 맡아 둔다 — 고객·반려동물 표는 건드리지 않는다. 등록·반영이 떼어 내 그 아이에게 붙인다."""
        assert self._signatures is not None
        shown = answer.pet_name or await self._reader.pet_name(ctx, form) or ""
        await self._signatures.add(ctx, NewSignature(
            customer_id=None, form_id=None, channel="intake", signer_name=consent.signer_name,
            signature_png=consent.signature_png, signed_at=now, by_member_id=form.created_by_member_id,
            intake_answer_id=answer_id,
            pets=(NewSignaturePet(
                pet_id=None, shown_pet_name=shown,
                parts=tuple(SignedPart(part, layout.texts[part].source, layout.texts[part].version)
                            for part in PARTS if part in consent.parts),
                condition_labels=shown_conditions(answer, dict(layout.condition_types)),
            ),),
        ))

