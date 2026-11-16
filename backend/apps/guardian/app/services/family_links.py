"""가족 연결의 공통 단계(⑫). 잠금 순서: 유저 행 → 기본 연결 행 → 가족 초대 행 → 가족 연결 행."""
from __future__ import annotations

from datetime import datetime

from guardian.app.ports.output.family_invite_repository import FamilyInviteRepository
from guardian.app.ports.output.guardian_link_repository import GuardianLinkRepository
from guardian.domain.entities.guardian_link import GuardianLink
from guardian.domain.errors import GuardianLinkNotFoundError


async def locked_primary(links: GuardianLinkRepository, user_id: int, link_id: int) -> GuardianLink:
    """내 기본 연결을 잠가 준다. 없거나 남의 것이거나 가족 연결이면 404 — 가족이 있는지 드러내지 않는다."""
    link = await links.get_live(user_id, link_id)
    primary = None if link is None or link.is_family else await links.lock_primary(link.id)
    if primary is None:
        raise GuardianLinkNotFoundError("연결을 찾을 수 없습니다.")
    return primary


async def end_primary(
    links: GuardianLinkRepository, invites: FamilyInviteRepository, primary: GuardianLink, ended_by: str,
    now: datetime,
) -> None:
    """기본 연결을 끝낸다 — 안 쓴 초대를 죽이고, 가족 연결을 같은 사유로 끝내고, 기본 연결을 끝낸다.
    부르기 전에 기본 연결 행을 잠근다."""
    await invites.revoke_unused([primary.id], now)
    await links.end_family([primary.id], ended_by, now)
    if not await links.end(primary.id, ended_by, now):
        raise GuardianLinkNotFoundError("연결을 찾을 수 없습니다.")
