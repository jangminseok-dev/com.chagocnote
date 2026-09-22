from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Customer:
    """살아 있는(익명화하지 않은) 보호자. 익명화한 고객은 엔티티로 읽지 않는다 — 없는 것으로 본다."""

    id: int
    shop_id: int
    name: str
    phone: str
    phone_alt: str | None
    marketing_consent: bool
    marketing_consent_changed_at: datetime
    memo: str | None
