from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field, StrictInt

from visit.adapter.inbound.api.schemas.create_menu_schema import MenuName, Price


class UpdateMenuRequestSchema(BaseModel):
    """전체 교체다. 정가를 보내지 않으면 가격 미정(None)이 된다 — ④ 이전 앱도 그대로 부를 수 있게 기본값을 둔다."""

    name: MenuName
    default_duration_minutes: StrictInt | None
    sort_order: Annotated[StrictInt, Field(ge=0, le=9_999)]
    price: Price | None = None
