from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class CreateFamilyInviteCommand:
    user_id: int
    link_id: int


@dataclass(frozen=True)
class FamilyInviteResult:
    code: str = field(repr=False)   # 원문은 이번 응답에만 — 로그·repr 에 남기지 않는다
    expires_at: datetime


@dataclass(frozen=True)
class JoinFamilyCommand:
    user_id: int
    code: str | None = field(repr=False)


@dataclass(frozen=True)
class JoinFamilyResult:
    link_id: int
    created: bool


@dataclass(frozen=True)
class ListFamilyQuery:
    user_id: int
    link_id: int


@dataclass(frozen=True)
class FamilyMemberView:
    """가족 한 사람 — 이은 순서의 번호로만 보인다. 이름·계정은 담지 않는다."""

    family_id: int
    linked_at: datetime   # 매장 시간대
    unseen: bool          # 기본 보호자가 아직 보지 않은 새 줄


@dataclass(frozen=True)
class EndFamilyMemberCommand:
    user_id: int
    link_id: int
    family_id: int


@dataclass(frozen=True)
class EndAllFamilyCommand:
    user_id: int
    link_id: int


@dataclass(frozen=True)
class GetGuardianSettingsQuery:
    ctx: ShopContext


@dataclass(frozen=True)
class UpdateGuardianSettingsCommand:
    ctx: ShopContext
    family_max: int


@dataclass(frozen=True)
class GuardianSettingsView:
    family_max: int
    default_family_max: int
