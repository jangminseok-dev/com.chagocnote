"""받은 문진표를 읽고 쓰는 작은 규칙들(⑪ 설계 3.4) — 보관 기간, 보이는 모양, 등록이 답을 쓰고 지우기(맡아 둔 서명을 옮기기)."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from customer.app.dtos.intake_answer_view_dto import IntakeAnswerView
from customer.app.ports.output.condition_type_repository import ConditionTypeRepository
from customer.app.ports.output.consent_signature_repository import ConsentSignatureRepository
from customer.app.ports.output.customer_repository import CustomerRepository
from customer.app.ports.output.form_settings_repository import FormSettingsRepository
from customer.app.ports.output.intake_answer_repository import IntakeAnswerRepository
from customer.app.ports.output.pet_repository import PetRepository
from customer.app.services.consent_reader import facts_of
from customer.app.services.consent_source import ConsentSource
from customer.domain.entities.consent_form import HeldSignature
from customer.domain.entities.intake import IntakeAnswer
from customer.domain.errors import IntakeAnswerNotFoundError
from customer.domain.services.consent_coverage import uncovered
from customer.domain.services.intake_summary import memo_draft, memo_over, missing_fields
from hub.app.dtos.shop_context import ShopContext


async def kept_since(ctx: ShopContext, now: datetime, settings: FormSettingsRepository) -> datetime:
    """이 시각보다 앞서 받은 답은 없는 것으로 친다 — 주기 작업이 지우기 전이라도."""
    return now - timedelta(days=(await settings.get(ctx)).intake_keep_days)


async def describe_answers(
    ctx: ShopContext, answers: list[IntakeAnswer], *, customers: CustomerRepository, pets: PetRepository,
    condition_types: ConditionTypeRepository,
) -> list[IntakeAnswerView]:
    if not answers:
        return []
    owners = sorted({a.matched_customer_id for a in answers if a.matched_customer_id is not None})
    names = {c.id: c.name for c in await customers.list_active(ctx, owners)} if owners else {}
    pet_names = {p.id: p.name for p in await pets.list_for_customers(ctx, owners)} if owners else {}
    labels = {t.code: t.label for t in await condition_types.list_all()}
    zone = ZoneInfo(ctx.timezone)
    views = []
    for answer in answers:
        draft = memo_draft(answer)
        views.append(IntakeAnswerView(
            answer=answer, pet_name=answer.pet_name or pet_names.get(answer.pet_id),
            submitted_on=answer.submitted_at.astimezone(zone).date(),
            matched_customer_name=names.get(answer.matched_customer_id), condition_labels=labels,
            missing=missing_fields(answer), memo_draft=draft, memo_over=memo_over(draft),
        ))
    return views


class IntakeAnswerUse:
    """등록·반영이 받은 문진표를 쓴다(⑪ 설계 3.4·5.4). 같은 트랜잭션 안에서 —

    1. 맨 앞 `check` — 그 답이 이 대상의 것인지 본다. 없거나 어긋나면 404 이고 아무것도 쓰지 않는다.
    2. 아이를 저장한 뒤 `finish` — 맡아 둔 동의서 서명을 그 아이에게 옮겨 붙이고(⑪-C1b) 답을 지운다.
       지울 답이 없으면(그 사이 다른 기기가 썼다) 404 — 트랜잭션이 통째로 되돌아가 고객이 둘 생기지 않는다.

    서명은 그 아이에게 살아 있는 동의가 없을 때만 받은 날을 찍는다 — 서명한 날(매장 시간대)로. 살아 있으면 덮는 것만 는다.
    맡아 둔 서명은 자기가 보인 토막과 지병 이름만 덮는다 — 사장이 지병을 더했으면 그 토막이 남는다.
    """

    def __init__(
        self, answers: IntakeAnswerRepository, signatures: ConsentSignatureRepository | None = None,
        pets: PetRepository | None = None, source: ConsentSource | None = None,
    ) -> None:
        self._answers = answers
        self._signatures = signatures
        self._pets = pets
        self._source = source or ConsentSource()

    async def check(
        self, ctx: ShopContext, answer_id: int | None, *, customer_id: int | None = None, pet_id: int | None = None,
    ) -> None:
        """**답은 그 답을 받은 대상에게만 쓴다.** 새 고객 등록(둘 다 None)은 새 손님용 링크의 답만, 아이 더하기(customer_id)는
        그 고객에게 보낸 링크나 새 손님용 링크의 답만, 아이 고치기(pet_id)는 그 아이의 다시 받기 답만. 어긋나면 없는 답으로
        친다 — 엉뚱한 보호자가 낸 문진표가 등록되지도 않은 채 사라지지 않는다.
        """
        if answer_id is None:
            return
        target = await self._answers.target_of(ctx, answer_id)
        if target is not None:
            form_customer, form_pet = target
            if pet_id is not None:
                fits = form_pet == pet_id
            else:
                fits = form_pet is None and form_customer in (None, customer_id)
            if fits:
                return
        raise IntakeAnswerNotFoundError("받은 문진표를 찾을 수 없습니다.")

    async def finish(
        self, ctx: ShopContext, answer_id: int | None, *, customer_id: int, pet_id: int, today: date,
    ) -> None:
        if answer_id is None:
            return
        held = None
        if self._signatures is not None:
            # 답을 지우면 매달린 서명도 지워진다(CASCADE) — 먼저 떼어 낸다.
            held = await self._signatures.adopt_held(ctx, answer_id, customer_id=customer_id, pet_id=pet_id)
        if not await self._answers.delete(ctx, answer_id):
            raise IntakeAnswerNotFoundError("받은 문진표를 찾을 수 없습니다.")
        if held is not None:
            await self._stamp(ctx, pet_id, held, today)

    async def _stamp(self, ctx: ShopContext, pet_id: int, held: HeldSignature, today: date) -> None:
        assert self._pets is not None and self._signatures is not None
        pet = await self._pets.get(ctx, pet_id)
        since = ({pet.id: pet.grooming_consent_signature_id}
                 if pet.grooming_consent_on is not None and pet.grooming_consent_signature_id is not None else {})
        covers = await self._signatures.covers(ctx, since)
        _, full = uncovered(facts_of(pet, covers.get(pet.id, ())), today, await self._source.policy(ctx))
        if full:
            signed_on = held.signed_at.astimezone(ZoneInfo(ctx.timezone)).date()
            await self._pets.set_grooming_consent(ctx, pet_id, signed_on, held.by_member_id, held.signature_id)
