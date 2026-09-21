from __future__ import annotations

from tenancy.app.dtos.remove_member_dto import RemoveMemberCommand
from tenancy.app.ports.input.remove_member_use_case import RemoveMemberUseCase
from tenancy.app.ports.output.member_repository import MemberRepository
from tenancy.domain.errors import MemberNotFoundError
from tenancy.domain.services.owner_guard import ensure_owner_remains
from tenancy.domain.value_objects.role_code import RoleCode


class RemoveMemberInteractor(RemoveMemberUseCase):
    """행을 지우지 않고 removed_at 을 남긴다. 내보낸 멤버는 다음 요청부터 소속 확인에서 걸린다."""

    def __init__(self, members: MemberRepository) -> None:
        self._members = members

    async def remove(self, command: RemoveMemberCommand) -> None:
        target = await self._members.get_active(command.ctx, command.member_id)
        if target is None:
            raise MemberNotFoundError("멤버를 찾을 수 없습니다.")
        if target.role is RoleCode.OWNER:
            ensure_owner_remains(await self._members.count_owners(command.ctx))
        await self._members.remove(command.ctx, target.id)
