from __future__ import annotations

from dataclasses import dataclass

from auth.domain.value_objects.provider import Provider


@dataclass(frozen=True)
class SocialIdentity:
    id: int
    user_id: int
    provider: Provider
    provider_user_id: str
    email: str | None
