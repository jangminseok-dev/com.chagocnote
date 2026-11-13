from __future__ import annotations

from guardian.adapter.outbound.orm.guardian_orm import GuardianLinkOrm
from guardian.domain.entities.guardian_link import GuardianLink


def to_link(orm: GuardianLinkOrm) -> GuardianLink:
    return GuardianLink(
        id=orm.id, user_id=orm.user_id, shop_id=orm.shop_id, customer_id=orm.customer_id,
        verified_by=orm.verified_by, created_at=orm.created_at, ended_at=orm.ended_at, ended_by=orm.ended_by,
    )
