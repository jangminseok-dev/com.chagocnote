from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.membership_summary import MembershipSummary


@dataclass(frozen=True)
class GetMeQuery:
    user_id: int


@dataclass(frozen=True)
class MeResponse:
    id: int
    display_name: str
    profile_image_url: str | None
    identities: tuple[str, ...]
    shops: tuple[MembershipSummary, ...]
