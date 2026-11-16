"""문진표 보내기의 요청(⑪-C, 매장용). 응답은 동의서 보내기와 같은 `FormLinkSchema` 다."""
from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field

_MAX_BIGINT = 9_223_372_036_854_775_807
_Id = Annotated[int, Field(ge=1, le=_MAX_BIGINT)]


class IssueIntakeFormRequestSchema(BaseModel):
    """둘 다 없으면 새 손님, 고객만 있으면 그 고객의 새 아이, 아이가 있으면 그 아이의 정보를 다시 받는다."""

    customer_id: _Id | None = None
    pet_id: _Id | None = None
