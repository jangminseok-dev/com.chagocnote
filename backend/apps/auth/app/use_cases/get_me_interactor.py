from __future__ import annotations

from auth.app.dtos.get_me_dto import GetMeQuery, MeResponse
from auth.app.ports.input.get_me_use_case import GetMeUseCase
from auth.app.ports.output.user_repository import UserRepository
from auth.domain.errors import UserNotFoundError


class GetMeInteractor(GetMeUseCase):
    def __init__(self, users: UserRepository) -> None:
        self._users = users

    async def get_me(self, query: GetMeQuery) -> MeResponse:
        user = await self._users.get(query.user_id)
        if user is None:
            raise UserNotFoundError("다시 로그인해 주세요.")
        identities = await self._users.list_identities(user.id)
        return MeResponse(
            id=user.id,
            display_name=user.display_name,
            profile_image_url=user.profile_image_url,
            identities=tuple(i.provider.value for i in identities),
        )
