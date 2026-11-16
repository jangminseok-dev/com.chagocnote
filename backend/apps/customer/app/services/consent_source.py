"""동의서의 기준값을 매장의 설정에서 읽는다(⑪-B). 발급·문서 읽기·서명이 함께 쓴다."""
from __future__ import annotations

from customer.app.ports.output.form_settings_repository import FormSettingsRepository
from customer.domain.entities.consent import ConsentPolicy
from hub.app.dtos.shop_context import ShopContext


class ConsentSource:
    """저장소를 주지 않으면 기본값이다(단위 테스트)."""

    def __init__(self, settings: FormSettingsRepository | None = None) -> None:
        self._settings = settings

    async def policy(self, ctx: ShopContext) -> ConsentPolicy:
        if self._settings is None:
            return ConsentPolicy()
        return (await self._settings.get(ctx)).policy
