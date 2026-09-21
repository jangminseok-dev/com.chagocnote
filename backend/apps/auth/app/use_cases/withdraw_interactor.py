from __future__ import annotations

from auth.app.dtos.withdraw_dto import WithdrawCommand, WithdrawResult
from auth.app.ports.input.withdraw_use_case import WithdrawUseCase
from auth.app.ports.output.operator_repository import OperatorRepository
from auth.app.ports.output.refresh_token_store_port import RefreshTokenStorePort
from auth.app.ports.output.user_repository import UserRepository
from auth.domain.errors import AccountSuspendedError
from hub.app.ports.membership_lifecycle_port import MembershipLifecyclePort


class WithdrawInteractor(WithdrawUseCase):
    """탈퇴는 즉시 처리되고 되돌릴 수 없다. DB 변경은 요청 하나의 트랜잭션이라, 어디서든 실패하면
    전부 되돌아간다 — "익명화는 됐는데 신원은 남은" 중간 상태가 생기지 않는다."""

    def __init__(
        self, users: UserRepository, operators: OperatorRepository,
        lifecycle: MembershipLifecyclePort, store: RefreshTokenStorePort,
    ) -> None:
        self._users = users
        self._operators = operators
        self._lifecycle = lifecycle
        self._store = store

    async def withdraw(self, command: WithdrawCommand) -> WithdrawResult:
        # 같은 유저의 연결·해제·다른 탈퇴 요청과 겹치지 않게 잠그고 다시 읽는다.
        user = await self._users.lock(command.user_id)
        if user is None or user.is_deleted:
            return WithdrawResult(revocations=())
        if user.is_suspended:
            # 요청 가드(core/security.py)가 정지된 유저를 먼저 막지만, 가드를 통과한 뒤 잠금을
            # 얻는 사이에 정지가 걸릴 수 있다. 그대로 진행하면 정지된 계정의 소속을 지우고 신원까지
            # 없애 버리게 된다.
            raise AccountSuspendedError("정지된 계정입니다.")
        # 소속을 먼저 정리한다. 혼자 사장인 매장 때문에 막히면 여기서 오류로 끝나고 아무것도 바뀌지 않는다.
        await self._lifecycle.apply_withdrawal(user.id, command.confirm_close_shops)
        # 신원을 지우기 전에, 제공자 쪽 연결을 끊는 데 필요한 것을 읽어 둔다.
        revocations = await self._users.list_revocations(user.id)
        await self._operators.revoke(user.id)
        await self._users.anonymize(user.id)
        await self._users.delete_identities(user.id)
        await self._store.revoke_all(user.id)
        return WithdrawResult(revocations=tuple(revocations))
