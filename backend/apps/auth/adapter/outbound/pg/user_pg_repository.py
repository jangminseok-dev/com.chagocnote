from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.adapter.outbound.gateways.fernet_cipher import FernetCipher
from auth.adapter.outbound.mappers.user_mapper import to_identity, to_user
from auth.adapter.outbound.orm.user_orm import SocialIdentityOrm, UserOrm
from auth.app.ports.output.user_repository import UserRepository
from auth.domain.entities.social_identity import SocialIdentity
from auth.domain.entities.user import User
from auth.domain.value_objects.provider import Provider
from auth.domain.value_objects.social_profile import SocialProfile


class UserPgRepository(UserRepository):
    def __init__(self, session: AsyncSession, cipher: FernetCipher) -> None:
        self._session = session
        self._cipher = cipher

    async def find_by_identity(self, provider: Provider, provider_user_id: str) -> User | None:
        stmt = (
            select(UserOrm)
            .join(SocialIdentityOrm, SocialIdentityOrm.user_id == UserOrm.id)
            .where(
                SocialIdentityOrm.provider == provider.value,
                SocialIdentityOrm.provider_user_id == provider_user_id,
            )
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return to_user(row) if row else None

    async def create_with_identity(self, profile: SocialProfile) -> User:
        user = UserOrm(
            display_name=(profile.display_name or "이름 없음")[:50],
            profile_image_url=profile.profile_image_url,
        )
        self._session.add(user)
        await self._session.flush()
        token = profile.provider_refresh_token
        self._session.add(
            SocialIdentityOrm(
                user_id=user.id,
                provider=profile.provider.value,
                provider_user_id=profile.provider_user_id,
                email=profile.email,
                provider_refresh_token_enc=self._cipher.encrypt(token) if token else None,
            )
        )
        await self._session.flush()
        return to_user(user)

    async def get(self, user_id: int) -> User | None:
        row = await self._session.get(UserOrm, user_id)
        return to_user(row) if row else None

    async def list_identities(self, user_id: int) -> list[SocialIdentity]:
        stmt = (
            select(SocialIdentityOrm)
            .where(SocialIdentityOrm.user_id == user_id)
            .order_by(SocialIdentityOrm.id)
        )
        return [to_identity(r) for r in (await self._session.execute(stmt)).scalars()]
