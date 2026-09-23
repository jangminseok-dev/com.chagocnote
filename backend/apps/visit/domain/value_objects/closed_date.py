from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class ClosedDate:
    """임시 휴무일 하나."""

    day: date
    note: str | None
