from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from auth.adapter.outbound.gateways.fernet_cipher import FernetCipher
from auth.adapter.outbound.mappers.user_mapper import to_identity, to_user
from auth.adapter.outbound.orm.user_orm import SocialIdentityOrm, UserOrm
from auth.app.ports.output.user_repository import UserRepository
from auth.domain.entities.social_identity import SocialIdentity
from auth.domain.entities.user import User
from auth.domain.errors import IdentityAlreadyLinkedError
from auth.domain.value_objects.provider import Provider
from auth.domain.value_objects.social_profile import SocialProfile


class UserPgRepository(UserRepository):
    def __init__(self, session: AsyncSession, cipher: FernetCipher | None = None) -> None:
        """cipher 는 인증 프로세스만 넘긴다. 읽기만 하는 경로(API 프로세스)는 없이 조립한다."""
        self._session = session
        self._cipher = cipher

    def _require_cipher(self) -> FernetCipher:
        if self._cipher is None:
            raise RuntimeError("암호화 도구 없이 조립된 리포지토리는 제공자 토큰을 다룰 수 없습니다.")
        return self._cipher

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
        token = profile.provider_refresh_token
        encrypted = self._require_cipher().encrypt(token) if token else None
        user = UserOrm(
            display_name=(profile.display_name or "이름 없음")[:50],
            profile_image_url=profile.profile_image_url,
        )
        try:
            # 유저와 신원을 한 세이브포인트에 넣는다. 신원의 유일 제약에 걸리면 유저 행도 함께 되돌아간다.
            async with self._session.begin_nested():
                self._session.add(user)
                await self._session.flush()
                self._session.add(
                    SocialIdentityOrm(
                        user_id=user.id,
                        provider=profile.provider.value,
                        provider_user_id=profile.provider_user_id,
                        email=profile.email,
                        provider_refresh_token_enc=encrypted,
                    )
                )
                await self._session.flush()
        except IntegrityError as exc:
            if _constraint(exc) != "uq_social_identities_provider_user":
                raise
            raise IdentityAlreadyLinkedError("이미 다른 계정에 연결된 로그인 수단입니다.") from exc
        return to_user(user)

    async def fill_provider_refresh_token(
        self, provider: Provider, provider_user_id: str, token: str
    ) -> None:
        await self._session.execute(
            update(SocialIdentityOrm)
            .where(
                SocialIdentityOrm.provider == provider.value,
                SocialIdentityOrm.provider_user_id == provider_user_id,
                SocialIdentityOrm.provider_refresh_token_enc.is_(None),
            )
            .values(provider_refresh_token_enc=self._require_cipher().encrypt(token))
        )

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

    async def list_by_ids(self, user_ids: Sequence[int]) -> list[User]:
        if not user_ids:
            return []
        stmt = select(UserOrm).where(UserOrm.id.in_(user_ids))
        return [to_user(row) for row in (await self._session.execute(stmt)).scalars()]


def _constraint(exc: IntegrityError) -> str | None:
    """asyncpg 는 제약 이름을 원인 예외에 담고, SQLAlchemy 는 그것을 __cause__ 로 감싼다."""
    return getattr(exc.orig.__cause__, "constraint_name", None)
