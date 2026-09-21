from __future__ import annotations

from tenancy.app.dtos.remove_member_dto import RemoveMemberCommand
from tenancy.app.ports.input.remove_member_use_case import RemoveMemberUseCase
from tenancy.app.ports.output.invite_repository import InviteRepository
from tenancy.app.ports.output.member_repository import MemberRepository
from tenancy.domain.errors import MemberNotFoundError
from tenancy.domain.services.owner_guard import ensure_owner_remains
from tenancy.domain.value_objects.role_code import RoleCode


class RemoveMemberInteractor(RemoveMemberUseCase):
    """행을 지우지 않고 removed_at 을 남긴다. 내보낸 멤버는 다음 요청부터 소속 확인에서 걸린다."""

    def __init__(self, members: MemberRepository, invites: InviteRepository) -> None:
        self._members = members
        self._invites = invites

    async def remove(self, command: RemoveMemberCommand) -> None:
        # 대상을 읽기 전에 매장 단위로 직렬화한다. 낡은 역할로 마지막 사장을 내보내지 않게 한다.
        await self._members.lock_membership_changes(command.ctx)
        target = await self._members.get_active(command.ctx, command.member_id)
        if target is None:
            raise MemberNotFoundError("멤버를 찾을 수 없습니다.")
        if target.role is RoleCode.OWNER:
            ensure_owner_remains(await self._members.count_owners(command.ctx))
        await self._members.remove(command.ctx, target.id)
        # 내보낸 멤버가 미리 만들어 둔 초대로 다시 들어오지 못하게 같은 트랜잭션에서 무효화한다.
        await self._invites.revoke_created_by(command.ctx, target.id)
