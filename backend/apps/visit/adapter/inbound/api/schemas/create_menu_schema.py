from __future__ import annotations

from typing import Annotated

from pydantic import AfterValidator, BaseModel, StrictInt, StringConstraints

from visit.adapter.inbound.api.schemas.text_validators import reject_control_chars

MenuName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30),
    AfterValidator(reject_control_chars),
]


class CreateMenuRequestSchema(BaseModel):
    """기본 소요를 비우면 매장 기본 소요를 쓴다."""

    name: MenuName
    default_duration_minutes: StrictInt | None = None
