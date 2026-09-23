from __future__ import annotations

from datetime import date
from typing import Annotated

from pydantic import AfterValidator, BaseModel, StringConstraints

from visit.adapter.inbound.api.schemas.text_validators import reject_control_chars


class AddClosedDateRequestSchema(BaseModel):
    date: date
    note: Annotated[
        str, StringConstraints(strip_whitespace=True, max_length=30), AfterValidator(reject_control_chars)
    ] | None = None
