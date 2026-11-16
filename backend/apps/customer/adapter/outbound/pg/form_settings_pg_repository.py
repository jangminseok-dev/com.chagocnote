from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from customer.adapter.outbound.orm.form_settings_orm import ShopFormSettingsOrm
from customer.app.ports.output.form_settings_repository import FormSettingsRepository
from customer.domain.value_objects.form_settings import DEFAULT_FORM_SETTINGS, FormSettings
from hub.app.dtos.shop_context import ShopContext


class FormSettingsPgRepository(FormSettingsRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, ctx: ShopContext) -> FormSettings:
        row = (
            await self._session.execute(
                select(ShopFormSettingsOrm).where(ShopFormSettingsOrm.shop_id == ctx.shop_id)
                .execution_options(populate_existing=True)
            )
        ).scalar_one_or_none()
        if row is None:
            return DEFAULT_FORM_SETTINGS
        return FormSettings(
            link_days=row.link_days, senior_age=row.senior_age, consent_days=row.consent_days,
            reservation_text=row.reservation_text, consent_text=row.consent_text,
            intake_keep_days=row.intake_keep_days, intake_hidden=tuple(row.intake_hidden),
            intake_consent_all=row.intake_consent_all,
        )

    async def put(self, ctx: ShopContext, settings: FormSettings) -> FormSettings:
        values = {
            "link_days": settings.link_days, "senior_age": settings.senior_age,
            "consent_days": settings.consent_days, "reservation_text": settings.reservation_text,
            "consent_text": settings.consent_text,
            "intake_keep_days": settings.intake_keep_days, "intake_hidden": list(settings.intake_hidden),
            "intake_consent_all": settings.intake_consent_all,
        }
        await self._session.execute(
            insert(ShopFormSettingsOrm).values(shop_id=ctx.shop_id, **values)
            .on_conflict_do_update(index_elements=["shop_id"], set_={**values, "updated_at": func.now()})
        )
        return await self.get(ctx)
