from __future__ import annotations

from collections.abc import Sequence

from auth.app.ports.output.user_repository import UserRepository
from hub.app.dtos.user_profile import UserProfile
from hub.app.ports.user_directory_port import UserDirectoryPort


class GetUserProfilesInteractor(UserDirectoryPort):
    """허브의 UserDirectoryPort 구현. 입력 포트가 곧 허브 포트다."""

    def __init__(self, users: UserRepository) -> None:
        self._users = users

    async def get_profiles(self, user_ids: Sequence[int]) -> dict[int, UserProfile]:
        return {
            user.id: UserProfile(
                user_id=user.id,
                display_name=user.display_name,
                profile_image_url=user.profile_image_url,
            )
            for user in await self._users.list_by_ids(user_ids)
        }
