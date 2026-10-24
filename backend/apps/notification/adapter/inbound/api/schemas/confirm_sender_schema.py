from __future__ import annotations

from pydantic import BaseModel

from notification.adapter.inbound.api.schemas.onboarding_fields import SenderPhone, SixDigits


class ConfirmSenderRequestSchema(BaseModel):
    phone: SenderPhone
    code: SixDigits
