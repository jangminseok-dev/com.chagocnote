from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LinkIdentityCommand:
    user_id: int
    provider: str
    token: str
    authorization_code: str | None
    nonce: str | None


@dataclass(frozen=True)
class LinkedIdentities:
    identities: tuple[str, ...]
