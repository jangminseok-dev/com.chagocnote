from __future__ import annotations

from abc import ABC, abstractmethod

from customer.domain.value_objects.form_settings import FormSettings
from hub.app.dtos.shop_context import ShopContext


class FormSettingsRepository(ABC):
    """매장의 서류 설정."""

    @abstractmethod
    async def get(self, ctx: ShopContext) -> FormSettings:
        """정한 적이 없으면 기본값. 행을 만들지 않는다."""

    @abstractmethod
    async def put(self, ctx: ShopContext, settings: FormSettings) -> FormSettings:
        """전체를 바꾼다. 행이 없으면 만든다."""
