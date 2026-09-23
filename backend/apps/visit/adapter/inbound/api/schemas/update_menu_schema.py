from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field, StrictInt

from visit.adapter.inbound.api.schemas.create_menu_schema import MenuName


class UpdateMenuRequestSchema(BaseModel):
    name: MenuName
    default_duration_minutes: StrictInt | None
    sort_order: Annotated[StrictInt, Field(ge=0, le=32_767)]
