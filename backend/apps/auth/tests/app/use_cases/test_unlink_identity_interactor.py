from datetime import datetime, timezone

import pytest

from auth.app.dtos.token_dto import TokenPair
from auth.app.dtos.unlink_identity_dto import UnlinkIdentityCommand
from auth.app.use_cases.unlink_identity_interactor import UnlinkIdentityInteractor
from auth.domain.entities.user import User
from auth.domain.errors import (
    AccountSuspendedError,
    IdentityNotFoundError,
    LastIdentityError,
    UnsupportedProviderError,
    UserNotFoundError,
)
from auth.domain.value_objects.identity_revocation import IdentityRevocation
from auth.domain.value_objects.provider import Provider

KAKAO = IdentityRevocation(Provider.KAKAO, "kakao-100", None)
APPLE = IdentityRevocation(Provider.APPLE, "apple-1", "apple-refresh")


def _user(deleted=False, suspended=False):
    return User(id=5, display_name="두부 보호자", profile_image_url=None, phone=None,
                suspended_at=datetime.now(timezone.utc) if suspended else None,
                deleted_at=datetime.now(timezone.utc) if deleted else None)


class _StubUsers:
    def __init__(self, calls, revocations, user):
        self.calls = calls
        self.revocations = list(revocations)
        self.user = user

    async def lock(self, user_id):
        self.calls.append("lock")
        return self.user

    async def list_revocations(self, user_id):
        self.calls.append("list_revocations")
        return list(self.revocations)

    async def delete_identity(self, user_id, provider):
        self.calls.append(f"delete:{provider.value}")
        self.revocations = [r for r in self.revocations if r.provider is not provider]


class _StubStore:
    def __init__(self, calls):
        self.calls = calls

    async def revoke_all(self, user_id):
        self.calls.append("revoke_all")


class _StubSessions:
    def __init__(self, calls):
        self.calls = calls

    async def issue(self, user_id, generation=None):
        self.calls.append("issue")
        return TokenPair("new-access", "5.new-refresh", 900)


def _run(revocations=(KAKAO, APPLE), user=None):
    calls = []
    users = _StubUsers(calls, revocations, user if user is not None else _user())
    return UnlinkIdentityInteractor(users, _StubStore(calls), _StubSessions(calls)), calls


async def test_수단을_해제하면_모든_세션을_끊고_새_토큰과_끊을_신원을_돌려준다():
    """G5"""
    interactor, calls = _run()
    result = await interactor.unlink(UnlinkIdentityCommand(user_id=5, provider="apple"))
    assert calls == ["lock", "list_revocations", "delete:apple", "revoke_all", "issue"]
    assert result.identities == ("kakao",)
    assert result.tokens.refresh_token == "5.new-refresh"
    assert result.revocation == APPLE


async def test_마지막_로그인_수단은_해제할_수_없다():
    interactor, calls = _run(revocations=(KAKAO,))
    with pytest.raises(LastIdentityError):
        await interactor.unlink(UnlinkIdentityCommand(user_id=5, provider="kakao"))
    assert calls == ["lock", "list_revocations"]


async def test_연결되지_않은_수단은_IDENTITY_NOT_FOUND_다():
    interactor, calls = _run(revocations=(KAKAO, APPLE))
    with pytest.raises(IdentityNotFoundError):
        await interactor.unlink(UnlinkIdentityCommand(user_id=5, provider="google"))
    assert calls == ["lock", "list_revocations"]


async def test_모르는_제공자_이름은_거절한다():
    interactor, calls = _run()
    with pytest.raises(UnsupportedProviderError):
        await interactor.unlink(UnlinkIdentityCommand(user_id=5, provider="naver"))
    assert calls == []


async def test_잠근_뒤에_탈퇴한_유저면_아무것도_하지_않는다():
    interactor, calls = _run(user=_user(deleted=True))
    with pytest.raises(UserNotFoundError):
        await interactor.unlink(UnlinkIdentityCommand(user_id=5, provider="apple"))
    assert calls == ["lock"]


async def test_잠근_뒤에_보니_정지된_유저면_아무것도_하지_않는다():
    """요청 시작 때는 정지 전이었지만, 잠금을 얻는 사이 정지가 걸리면 잠근 뒤 다시 확인해 거절한다.
    거절하지 않으면 세션 전부를 폐기하고 방금 정지된 유저에게 새 토큰을 내주게 된다."""
    interactor, calls = _run(user=_user(suspended=True))
    with pytest.raises(AccountSuspendedError):
        await interactor.unlink(UnlinkIdentityCommand(user_id=5, provider="apple"))
    assert calls == ["lock"]
