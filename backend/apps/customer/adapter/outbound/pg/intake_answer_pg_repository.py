from __future__ import annotations

from datetime import datetime

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from customer.adapter.outbound.orm.intake_orm import (
    IntakeAnswerConditionOrm, IntakeAnswerExtraOrm, IntakeAnswerOrm,
)
from customer.adapter.outbound.orm.consent_orm import CustomerFormOrm
from customer.app.ports.output.intake_answer_repository import IntakeAnswerRepository
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

