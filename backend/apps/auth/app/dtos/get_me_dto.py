from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GetMeQuery:
    user_id: int


@dataclass(frozen=True)
class MeResponse:
    id: int
    display_name: str
    profile_image_url: str | None
    identities: tuple[str, ...]
