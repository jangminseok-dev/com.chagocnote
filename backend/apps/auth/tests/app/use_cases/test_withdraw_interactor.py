from datetime import datetime, timezone

import pytest

from auth.app.dtos.withdraw_dto import WithdrawCommand
from auth.app.use_cases.withdraw_interactor import WithdrawInteractor
from auth.domain.entities.user import User
from auth.domain.errors import AccountSuspendedError
from auth.domain.value_objects.identity_revocation import IdentityRevocation
from auth.domain.value_objects.provider import Provider
from hub.app.errors import WithdrawalOwnershipTransferRequiredError

KAKAO = IdentityRevocation(Provider.KAKAO, "kakao-100", None)
APPLE = IdentityRevocation(Provider.APPLE, "apple-1", "apple-refresh")


def _user(deleted=False, suspended=False):
    return User(id=5, display_name="두부 보호자", profile_image_url=None, phone=None,
                suspended_at=datetime.now(timezone.utc) if suspended else None,
                deleted_at=datetime.now(timezone.utc) if deleted else None)


class _StubUsers:
    def __init__(self, calls, user):
        self.calls = calls
        self.user = user

    async def lock(self, user_id):
        self.calls.append(f"lock:{user_id}")
        return self.user

    async def list_revocations(self, user_id):
        self.calls.append(f"list_revocations:{user_id}")
        return [KAKAO, APPLE]

    async def anonymize(self, user_id):
        self.calls.append(f"anonymize:{user_id}")

    async def delete_identities(self, user_id):
        self.calls.append(f"delete_identities:{user_id}")


class _StubOperators:
    def __init__(self, calls):
        self.calls = calls

    async def revoke(self, user_id):
        self.calls.append(f"revoke_operator:{user_id}")


class _StubLifecycle:
    def __init__(self, calls, blocked=False):
        self.calls = calls
        self.blocked = blocked
        self.seen = []

    async def apply_withdrawal(self, user_id, close_sole_owned):
        self.calls.append("apply_withdrawal")
        self.seen.append((user_id, close_sole_owned))
        if self.blocked:
            raise WithdrawalOwnershipTransferRequiredError("막힘")


class _StubStore:
    def __init__(self, calls):
        self.calls = calls

    async def revoke_all(self, user_id):
        self.calls.append(f"revoke_all:{user_id}")


def _run(user="default", blocked=False):
    calls = []
    lifecycle = _StubLifecycle(calls, blocked)
    interactor = WithdrawInteractor(
        _StubUsers(calls, _user() if user == "default" else user),
        _StubOperators(calls), lifecycle, _StubStore(calls),
    )
    return interactor, lifecycle, calls


async def test_잠그고_소속을_정리한_뒤에_익명화하고_신원을_지우고_세션을_끊는다():
    interactor, lifecycle, calls = _run()
    result = await interactor.withdraw(WithdrawCommand(user_id=5, confirm_close_shops=True))
    assert calls == [
        "lock:5", "apply_withdrawal", "list_revocations:5",
        "revoke_operator:5", "anonymize:5", "delete_identities:5", "revoke_all:5",
    ]
    assert lifecycle.seen == [(5, True)]
    # 신원을 지우기 전에 읽어 둔 것을 돌려준다. 커밋 뒤에 제공자 쪽 연결을 끊는 데 쓴다.
    assert result.revocations == (KAKAO, APPLE)


async def test_소속_정리가_막히면_계정은_건드리지_않는다():
    interactor, _, calls = _run(blocked=True)
    with pytest.raises(WithdrawalOwnershipTransferRequiredError):
        await interactor.withdraw(WithdrawCommand(user_id=5, confirm_close_shops=False))
    assert calls == ["lock:5", "apply_withdrawal"]


async def test_이미_탈퇴한_유저면_아무것도_하지_않는다():
    """H5 — 같은 유저의 탈퇴가 동시에 두 번 와도 두 번째는 잠금 뒤에 조용히 끝난다."""
    for user in (_user(deleted=True), None):
        interactor, _, calls = _run(user=user)
        result = await interactor.withdraw(WithdrawCommand(user_id=5, confirm_close_shops=True))
        assert calls == ["lock:5"]
        assert result.revocations == ()


async def test_잠근_뒤에_보니_정지된_유저면_아무것도_하지_않는다():
    """core/security.py 의 요청 가드가 정지된 유저를 먼저 막지만, 가드를 통과한 뒤 잠금을 얻는
    사이에 정지가 걸릴 수 있다. 그대로 진행하면 정지된 계정의 소속을 지우고 신원까지 없애 버린다."""
    interactor, lifecycle, calls = _run(user=_user(suspended=True))
    with pytest.raises(AccountSuspendedError):
        await interactor.withdraw(WithdrawCommand(user_id=5, confirm_close_shops=True))
    assert calls == ["lock:5"]
    assert lifecycle.seen == []
