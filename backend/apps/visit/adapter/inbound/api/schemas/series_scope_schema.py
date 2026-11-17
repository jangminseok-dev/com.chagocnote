"""`이 예약만 / 이후 전부`(⑭) 요청 칸 — 옮기기·고치기·취소가 함께 쓴다. 빠지면 지금처럼 `이 예약만` 이다."""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, StrictBool, field_validator

from visit.adapter.inbound.api.schemas.register_visit_schema import EntityId, unique_ids


class SeriesScopeFields(BaseModel):
    scope: Literal["this", "following"] = "this"   # following — 같은 묶음에서 이 회차와 뒤의 예약됨
    family: StrictBool = True                      # following 에서 거짓이면 요청한 방문의 아이만
    # 걸린 회차(409 VISIT_SERIES_CONFLICT 의 details)를 빼고 다시 보낼 때
    skip_visit_ids: Annotated[list[EntityId], Field(max_length=24)] = []

    _skip_unique = field_validator("skip_visit_ids")(unique_ids)
