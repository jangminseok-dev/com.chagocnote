from __future__ import annotations

from sqlalchemy import func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from customer.adapter.outbound.orm.intake_orm import ShopIntakeQuestionOrm
from customer.app.ports.output.intake_question_repository import IntakeQuestionRepository
from customer.domain.entities.intake import IntakeQuestion, QuestionDraft
from hub.app.dtos.shop_context import ShopContext


class IntakeQuestionPgRepository(IntakeQuestionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _live(self, ctx: ShopContext):
        return (ShopIntakeQuestionOrm.shop_id == ctx.shop_id, ShopIntakeQuestionOrm.removed_at.is_(None))

    async def list_live(self, ctx: ShopContext) -> list[IntakeQuestion]:
        rows = (
            await self._session.execute(
                select(ShopIntakeQuestionOrm).where(*self._live(ctx))
                .order_by(ShopIntakeQuestionOrm.position, ShopIntakeQuestionOrm.id)
                .execution_options(populate_existing=True)
            )
        ).scalars().all()
        return [IntakeQuestion(id=row.id, label=row.label, required=row.required) for row in rows]

    async def replace_all(self, ctx: ShopContext, drafts: tuple[QuestionDraft, ...]) -> list[IntakeQuestion]:
        kept = [draft.id for draft in drafts if draft.id is not None]
        await self._session.execute(
            update(ShopIntakeQuestionOrm).where(*self._live(ctx), ShopIntakeQuestionOrm.id.notin_(kept))
            .values(removed_at=func.now())
        )
        for position, draft in enumerate(drafts):
            if draft.id is None:
                await self._session.execute(insert(ShopIntakeQuestionOrm).values(
                    shop_id=ctx.shop_id, position=position, label=draft.label, required=draft.required))
            else:
                await self._session.execute(
                    update(ShopIntakeQuestionOrm).where(*self._live(ctx), ShopIntakeQuestionOrm.id == draft.id)
                    .values(position=position, label=draft.label, required=draft.required)
                )
        return await self.list_live(ctx)
