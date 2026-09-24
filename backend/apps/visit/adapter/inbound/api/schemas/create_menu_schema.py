from __future__ import annotations

from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field, StrictInt, StringConstraints

from visit.adapter.inbound.api.schemas.text_validators import reject_control_chars

MenuName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30),
    AfterValidator(reject_control_chars),
]
# 정가(원). 기록의 금액과 같은 상한이다(설계 9절 입력 경계).
Price = Annotated[StrictInt, Field(ge=0, le=100_000_000)]


class CreateMenuRequestSchema(BaseModel):
    """기본 소요를 비우면 매장 기본 소요를 쓴다. 정가를 비우면 가격 미정이다."""

    name: MenuName
    default_duration_minutes: StrictInt | None = None
    price: Price | None = None
