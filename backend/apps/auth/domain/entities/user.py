from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class User:
    id: int
    display_name: str
    profile_image_url: str | None
    phone: str | None
    suspended_at: datetime | None
    deleted_at: datetime | None

    @property
    def is_suspended(self) -> bool:
        return self.suspended_at is not None

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
