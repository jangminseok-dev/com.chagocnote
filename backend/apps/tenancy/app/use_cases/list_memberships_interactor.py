from __future__ import annotations

from hub.app.dtos.membership_summary import MembershipSummary
from hub.app.ports.membership_directory_port import MembershipDirectoryPort
from tenancy.app.ports.output.member_repository import MemberRepository


class ListMembershipsInteractor(MembershipDirectoryPort):
    """허브의 MembershipDirectoryPort 구현. 입력 포트가 곧 허브 포트다."""

    def __init__(self, members: MemberRepository) -> None:
        self._members = members

    async def list_for_user(self, user_id: int) -> list[MembershipSummary]:
        return await self._members.list_for_user(user_id)
