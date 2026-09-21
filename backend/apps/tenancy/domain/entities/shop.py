from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Shop:
    id: int
    name: str
    business_type: str
    phone: str | None
    address: str | None
    timezone: str
    suspended_at: datetime | None
    closed_at: datetime | None

    @property
    def is_closed(self) -> bool:
        return self.closed_at is not None
