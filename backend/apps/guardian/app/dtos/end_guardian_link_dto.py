from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EndGuardianLinkCommand:
    user_id: int
    link_id: int
