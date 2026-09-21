from __future__ import annotations

from tenancy.app.dtos.change_member_role_dto import ChangedMember, ChangeMemberRoleCommand
from tenancy.app.ports.input.change_member_role_use_case import ChangeMemberRoleUseCase
from tenancy.app.ports.output.invite_repository import InviteRepository
from tenancy.app.ports.output.member_repository import MemberRepository
from tenancy.domain.errors import MemberNotFoundError
from tenancy.domain.services.owner_guard import ensure_owner_remains
from tenancy.domain.value_objects.role_code import RoleCode


class ChangeMemberRoleInteractor(ChangeMemberRoleUseCase):
    def __init__(self, members: MemberRepository, invites: InviteRepository) -> None:
        self._members = members
        self._invites = invites

    async def change_role(self, command: ChangeMemberRoleCommand) -> ChangedMember:
        # 대상을 읽기 전에 매장 단위로 직렬화한다. 낡은 역할로 마지막 사장을 낮추지 않게 한다.
        await self._members.lock_membership_changes(command.ctx.shop_id)
        target = await self._members.get_active(command.ctx, command.member_id)
        if target is None:
            raise MemberNotFoundError("멤버를 찾을 수 없습니다.")
        new_role = RoleCode(command.role)
        if target.role is not new_role:
            if target.role is RoleCode.OWNER:
                # 사장 자리에서 빠지는 변경이다. 사장 행을 잠그고 센 뒤에 바꾼다.
                ensure_owner_remains(await self._members.count_owners(command.ctx))
            await self._members.change_role(command.ctx, target.id, new_role)
            if target.role is RoleCode.OWNER:
                # 초대를 만들 권한을 잃었다. 만들어 둔 초대도 같은 트랜잭션에서 무효화한다.
                await self._invites.revoke_created_by(command.ctx, target.id)
        return ChangedMember(member_id=target.id, user_id=target.user_id, role=new_role.value)
