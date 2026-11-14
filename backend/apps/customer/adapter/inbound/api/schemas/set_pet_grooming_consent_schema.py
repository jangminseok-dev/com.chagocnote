from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class SetPetGroomingConsentRequestSchema(BaseModel):
    received_on: date | None = None   # 없으면 오늘
