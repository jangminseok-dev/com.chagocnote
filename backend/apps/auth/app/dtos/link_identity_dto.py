from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class LinkIdentityCommand:
    user_id: int
    provider: str
    token: str = field(repr=False)
    authorization_code: str | None = field(repr=False)
    nonce: str | None


@dataclass(frozen=True)
class LinkedIdentities:
    identities: tuple[str, ...]
