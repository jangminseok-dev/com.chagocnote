from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field, StrictInt


class SetPetGroomingCycleRequestSchema(BaseModel):
    weeks: Annotated[StrictInt, Field(ge=1, le=52)]   # 1~52주
