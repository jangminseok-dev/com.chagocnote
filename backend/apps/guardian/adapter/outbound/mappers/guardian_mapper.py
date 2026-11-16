from __future__ import annotations

from guardian.adapter.outbound.orm.guardian_orm import GuardianFamilyInviteOrm, GuardianLinkOrm
from guardian.domain.entities.family_invite import FamilyInvite
from guardian.domain.entities.guardian_link import GuardianLink


def to_link(orm: GuardianLinkOrm) -> GuardianLink:
    return GuardianLink(
        id=orm.id, user_id=orm.user_id, shop_id=orm.shop_id, customer_id=orm.customer_id,
        verified_by=orm.verified_by, created_at=orm.created_at, ended_at=orm.ended_at, ended_by=orm.ended_by,
        parent_link_id=orm.parent_link_id, seen_by_primary_at=orm.seen_by_primary_at,
    )


def to_invite(orm: GuardianFamilyInviteOrm) -> FamilyInvite:
    return FamilyInvite(id=orm.id, link_id=orm.link_id, created_at=orm.created_at, expires_at=orm.expires_at,
                        used_at=orm.used_at, revoked_at=orm.revoked_at)
