from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from visit.adapter.inbound.api.schemas.register_visit_schema import EntityId


class AppendRecordMediaRequestSchema(BaseModel):
    media_id: EntityId
    phase: Literal["before", "after"]
