from __future__ import annotations

from dataclasses import dataclass

from customer.domain.value_objects.form_settings import FormSettings
from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class UpdateFormSettingsCommand:
    ctx: ShopContext
    settings: FormSettings
    kept: frozenset[str] = frozenset()   # 요청이 보내지 않은 칸의 이름 — 지금 값을 둔다(이 칸을 모르는 예전 앱)
