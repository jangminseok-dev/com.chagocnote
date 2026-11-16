from __future__ import annotations

from dataclasses import dataclass

from customer.domain.value_objects.form_settings import FormSettings
from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class UpdateFormSettingsCommand:
    ctx: ShopContext
    settings: FormSettings
