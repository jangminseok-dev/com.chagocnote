from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from auth.domain.entities.social_identity import SocialIdentity
from auth.domain.entities.user import User
from auth.domain.value_objects.identity_revocation import IdentityRevocation
from auth.domain.value_objects.provider import Provider
from auth.domain.value_objects.social_profile import SocialProfile


class UserRepository(ABC):
    @abstractmethod
    async def find_by_identity(self, provider: Provider, provider_user_id: str) -> User | None: ...

    @abstractmethod
    async def create_with_identity(self, profile: SocialProfile) -> User:
        """그 신원이 이미 있으면 IdentityAlreadyLinkedError (동시에 온 다른 요청이 먼저 만들었다)."""

    @abstractmethod
    async def fill_provider_refresh_token(
        self, provider: Provider, provider_user_id: str, token: str
    ) -> None:
        """저장된 값이 비어 있을 때만 채운다. 이미 있으면 덮어쓰지 않는다."""

    @abstractmethod
    async def get(self, user_id: int) -> User | None: ...

    @abstractmethod
    async def list_identities(self, user_id: int) -> list[SocialIdentity]: ...

    @abstractmethod
    async def list_by_ids(self, user_ids: Sequence[int]) -> list[User]: ...

    @abstractmethod
    async def lock(self, user_id: int) -> User | None:
        """유저 행을 잠그고 최신 값을 돌려준다. 계정을 바꾸는 유스케이스가 맨 앞에서 부른다.

        같은 유저의 연결·해제·탈퇴가 겹치지 않게 직렬화한다. 잠근 뒤에는 탈퇴 여부를 다시 본다.
        """

    @abstractmethod
    async def add_identity(self, user_id: int, profile: SocialProfile) -> None:
        """다른 유저의 신원이면 IdentityAlreadyLinkedError, 같은 제공자를 이미 가졌으면 ProviderAlreadyLinkedError."""

    @abstractmethod
    async def list_revocations(self, user_id: int) -> list[IdentityRevocation]:
        """제공자 쪽 연결을 끊는 데 필요한 것을 신원 ID 순으로 돌려준다. 신원을 지우기 전에 읽어 둔다."""

    @abstractmethod
    async def delete_identity(self, user_id: int, provider: Provider) -> None: ...

    @abstractmethod
    async def delete_identities(self, user_id: int) -> None: ...

    @abstractmethod
    async def anonymize(self, user_id: int) -> None:
        """행은 남긴다. 이름을 "탈퇴한 사용자"로 바꾸고 사진·전화번호를 지우고 탈퇴 시각을 남긴다.

        멱등이 아니다 — 이미 탈퇴한 유저에게 다시 부르면 탈퇴 시각이 밀린다. 부르는 쪽이 유저 행을
        잠근 뒤 탈퇴 여부를 다시 보고 부른다.
        """
