"""받은 문진표를 읽고 쓰는 작은 규칙들(⑪ 설계 3.4) — 보관 기간, 보이는 모양, 등록이 답을 쓰고 지우기."""
from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from customer.app.dtos.intake_answer_view_dto import IntakeAnswerView
from customer.app.ports.output.condition_type_repository import ConditionTypeRepository
from customer.app.ports.output.customer_repository import CustomerRepository
from customer.app.ports.output.form_settings_repository import FormSettingsRepository
from customer.app.ports.output.intake_answer_repository import IntakeAnswerRepository
from customer.app.ports.output.pet_repository import PetRepository
from customer.domain.entities.intake import IntakeAnswer
from customer.domain.errors import IntakeAnswerNotFoundError
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


async def consume_answer(ctx: ShopContext, answer_id: int | None, answers: IntakeAnswerRepository | None) -> None:
    """등록·반영이 받은 문진표를 썼다 — 같은 트랜잭션에서 답을 지운다. 답이 없으면(이미 썼거나 지웠다) 등록하지 않는다."""
    if answer_id is None:
        return
    if answers is None or not await answers.delete(ctx, answer_id):
        raise IntakeAnswerNotFoundError("받은 문진표를 찾을 수 없습니다.")
