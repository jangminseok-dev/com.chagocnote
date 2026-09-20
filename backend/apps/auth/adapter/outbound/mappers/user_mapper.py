from __future__ import annotations

from auth.adapter.outbound.orm.user_orm import SocialIdentityOrm, UserOrm
from auth.domain.entities.social_identity import SocialIdentity
from auth.domain.entities.user import User
from auth.domain.value_objects.provider import Provider


def to_user(orm: UserOrm) -> User:
    return User(
        id=orm.id,
        display_name=orm.display_name,
        profile_image_url=orm.profile_image_url,
        phone=orm.phone,
        suspended_at=orm.suspended_at,
        deleted_at=orm.deleted_at,
    )


def to_identity(orm: SocialIdentityOrm) -> SocialIdentity:
    return SocialIdentity(
        id=orm.id,
        user_id=orm.user_id,
        provider=Provider(orm.provider),
        provider_user_id=orm.provider_user_id,
        email=orm.email,
    )
