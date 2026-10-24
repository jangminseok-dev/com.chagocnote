from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from notification.adapter.inbound.api.schemas.onboarding_fields import SenderPhone


class RequestSenderVerificationRequestSchema(BaseModel):
    phone: SenderPhone


class SenderVerificationRequestedSchema(BaseModel):
    status: Literal["verification_requested"] = "verification_requested"
