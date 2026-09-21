from __future__ import annotations

from hub.app.ports.user_directory_port import UserDirectoryPort
from tenancy.app.dtos.list_members_dto import ListMembersQuery, MemberView
from tenancy.app.ports.input.list_members_use_case import ListMembersUseCase
from tenancy.app.ports.output.member_repository import MemberRepository


class ListMembersInteractor(ListMembersUseCase):
    def __init__(self, members: MemberRepository, users: UserDirectoryPort) -> None:
        self._members = members
        self._users = users

    async def list_members(self, query: ListMembersQuery) -> list[MemberView]:
        members = await self._members.list_active(query.ctx)
        # 유저는 지워지지 않는다 (탈퇴해도 익명화된 행이 남는다). 그래서 프로필은 언제나 있다.
        profiles = await self._users.get_profiles([m.user_id for m in members])
        return [
            MemberView(
                member_id=m.id,
                user_id=m.user_id,
                display_name=profiles[m.user_id].display_name,
                profile_image_url=profiles[m.user_id].profile_image_url,
                role=m.role.value,
                joined_at=m.joined_at,
            )
            for m in members
        ]
