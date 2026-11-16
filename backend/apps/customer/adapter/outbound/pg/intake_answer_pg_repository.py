from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from customer.adapter.outbound.orm.intake_orm import (
    IntakeAnswerConditionOrm, IntakeAnswerExtraOrm, IntakeAnswerOrm, ShopIntakeQuestionOrm,
)
from customer.adapter.outbound.orm.consent_orm import CustomerFormOrm
from customer.app.ports.output.intake_answer_repository import IntakeAnswerRepository
from customer.domain.entities.intake import ADD_PET, NEW, UPDATE, AnswerCondition, IntakeAnswer
from customer.domain.services.intake_rules import CleanAnswer
from hub.app.dtos.shop_context import ShopContext


class IntakeAnswerPgRepository(IntakeAnswerRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(
        self, ctx: ShopContext, form_id: int, answer: CleanAnswer, matched_customer_id: int | None, now: datetime,
    ) -> int:
        answer_id = (
            await self._session.execute(
                insert(IntakeAnswerOrm).values(
                    shop_id=ctx.shop_id, form_id=form_id, matched_customer_id=matched_customer_id,
                    guardian_name=answer.guardian_name, guardian_phone=answer.guardian_phone,
                    pet_name=answer.pet_name, species=answer.species, breed=answer.breed, sex=answer.sex,
                    neutered=answer.neutered, birth_date=answer.birth_date, birth_year=answer.birth_year,
                    birth_unknown=answer.birth_unknown, weight_kg=answer.weight_kg,
                    no_known_conditions=answer.no_known_conditions, dislikes=answer.dislikes, style=answer.style,
                    submitted_at=now,
                ).returning(IntakeAnswerOrm.id)
            )
        ).scalar_one()
        if answer.conditions:
            await self._session.execute(insert(IntakeAnswerConditionOrm), [
                {"answer_id": answer_id, "position": position, "type_code": entry.type_code,
                 "custom_label": entry.custom_label, "note": entry.note}
                for position, entry in enumerate(answer.conditions)
            ])
        if answer.extras:
            await self._session.execute(insert(IntakeAnswerExtraOrm), [
                {"answer_id": answer_id, "question_id": question_id, "body": body}
                for question_id, body in answer.extras
            ])
        # 받은 수는 요청 행에 적어 둔다 — 답을 지워도(등록·지우기) 한 링크의 한도가 다시 열리지 않는다.
        await self._session.execute(
            update(CustomerFormOrm).where(CustomerFormOrm.id == form_id)
            .values(intake_answered=CustomerFormOrm.intake_answered + 1)
        )
        return answer_id

    async def first_guardian(self, form_id: int) -> tuple[str, str] | None:
        row = (
            await self._session.execute(
                select(IntakeAnswerOrm.guardian_name, IntakeAnswerOrm.guardian_phone)
                .where(IntakeAnswerOrm.form_id == form_id, IntakeAnswerOrm.guardian_phone.is_not(None))
                .order_by(IntakeAnswerOrm.id).limit(1)
            )
        ).first()
        return None if row is None else (row.guardian_name, row.guardian_phone)


    async def list_since(self, ctx: ShopContext, since: datetime) -> list[IntakeAnswer]:
        return await self._read(
            IntakeAnswerOrm.shop_id == ctx.shop_id, IntakeAnswerOrm.submitted_at >= since)

    async def get(self, ctx: ShopContext, answer_id: int, since: datetime) -> IntakeAnswer | None:
        found = await self._read(
            IntakeAnswerOrm.shop_id == ctx.shop_id, IntakeAnswerOrm.id == answer_id,
            IntakeAnswerOrm.submitted_at >= since)
        return found[0] if found else None

    async def delete(self, ctx: ShopContext, answer_id: int) -> bool:
        return await self._delete(IntakeAnswerOrm.shop_id == ctx.shop_id, IntakeAnswerOrm.id == answer_id) > 0

    async def delete_for_customer(self, ctx: ShopContext, customer_id: int) -> None:
        theirs = select(CustomerFormOrm.id).where(
            CustomerFormOrm.shop_id == ctx.shop_id, CustomerFormOrm.customer_id == customer_id)
        await self._delete(
            IntakeAnswerOrm.shop_id == ctx.shop_id,
            (IntakeAnswerOrm.matched_customer_id == customer_id) | IntakeAnswerOrm.form_id.in_(theirs))

    async def delete_for_pet(self, ctx: ShopContext, pet_id: int) -> None:
        theirs = select(CustomerFormOrm.id).where(
            CustomerFormOrm.shop_id == ctx.shop_id, CustomerFormOrm.intake_pet_id == pet_id)
        await self._delete(IntakeAnswerOrm.shop_id == ctx.shop_id, IntakeAnswerOrm.form_id.in_(theirs))

    async def delete_older(self, ctx: ShopContext, before: datetime) -> int:
        return await self._delete(IntakeAnswerOrm.shop_id == ctx.shop_id, IntakeAnswerOrm.submitted_at < before)

    async def shops_with_answers(self) -> list[int]:
        return list((await self._session.execute(
            select(IntakeAnswerOrm.shop_id).distinct().order_by(IntakeAnswerOrm.shop_id))).scalars())

    async def _delete(self, *where) -> int:
        # 지병·질문의 답은 ON DELETE CASCADE 로 함께 지워진다.
        return (await self._session.execute(delete(IntakeAnswerOrm).where(*where))).rowcount

    async def _read(self, *where) -> list[IntakeAnswer]:
        rows = (
            await self._session.execute(
                select(IntakeAnswerOrm, CustomerFormOrm.customer_id, CustomerFormOrm.intake_pet_id)
                .join(CustomerFormOrm, CustomerFormOrm.id == IntakeAnswerOrm.form_id)
                .where(*where).order_by(IntakeAnswerOrm.submitted_at.desc(), IntakeAnswerOrm.id.desc())
                .execution_options(populate_existing=True)
            )
        ).all()
        if not rows:
            return []
        ids = [row[0].id for row in rows]
        conditions: dict[int, list[AnswerCondition]] = {answer_id: [] for answer_id in ids}
        for c in (await self._session.execute(
            select(IntakeAnswerConditionOrm).where(IntakeAnswerConditionOrm.answer_id.in_(ids))
            .order_by(IntakeAnswerConditionOrm.position)
        )).scalars():
            conditions[c.answer_id].append(AnswerCondition(c.type_code, c.custom_label, c.note))
        extras: dict[int, list[tuple[str, str]]] = {answer_id: [] for answer_id in ids}
        for answer_id, label, body in await self._session.execute(
            select(IntakeAnswerExtraOrm.answer_id, ShopIntakeQuestionOrm.label, IntakeAnswerExtraOrm.body)
            .join(ShopIntakeQuestionOrm, ShopIntakeQuestionOrm.id == IntakeAnswerExtraOrm.question_id)
            .where(IntakeAnswerExtraOrm.answer_id.in_(ids))
            .order_by(ShopIntakeQuestionOrm.position, ShopIntakeQuestionOrm.id)
        ):
            extras[answer_id].append((label, body))
        return [
            IntakeAnswer(
                id=a.id, form_id=a.form_id,
                mode=UPDATE if pet_id is not None else (NEW if customer_id is None else ADD_PET), pet_id=pet_id,
                matched_customer_id=a.matched_customer_id, guardian_name=a.guardian_name,
                guardian_phone=a.guardian_phone, pet_name=a.pet_name, species=a.species, breed=a.breed, sex=a.sex,
                neutered=a.neutered, birth_date=a.birth_date, birth_year=a.birth_year,
                birth_unknown=a.birth_unknown, weight_kg=a.weight_kg, no_known_conditions=a.no_known_conditions,
                conditions=tuple(conditions[a.id]), dislikes=a.dislikes, style=a.style,
                extras=tuple(extras[a.id]), submitted_at=a.submitted_at,
            )
            for a, customer_id, pet_id in rows
        ]
