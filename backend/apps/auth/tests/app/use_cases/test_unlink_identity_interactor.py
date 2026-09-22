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
        self.calls.append(f"lock:{user_id}")
        return self.user

    async def list_revocations(self, user_id):
        self.calls.append(f"list_revocations:{user_id}")
        return list(self.revocations)

    async def delete_identity(self, user_id, provider):
        self.calls.append(f"delete:{user_id}:{provider.value}")
        self.revocations = [r for r in self.revocations if r.provider is not provider]


class _StubStore:
    def __init__(self, calls):
        self.calls = calls

    async def revoke_all(self, user_id):
        self.calls.append(f"revoke_all:{user_id}")


class _StubSessions:
    def __init__(self, calls):
        self.calls = calls

    async def issue(self, user_id, generation=None, *, auth_time=None, fresh_login=False):
        self.calls.append(f"issue:{user_id}:{generation}:{auth_time}:{fresh_login}")
        return TokenPair("new-access", "5.new-refresh", 900)


def _run(revocations=(KAKAO, APPLE), user=None):
    calls = []
    users = _StubUsers(calls, revocations, user if user is not None else _user())
    return UnlinkIdentityInteractor(users, _StubStore(calls), _StubSessions(calls)), calls


async def test_수단을_해제하면_모든_세션을_끊고_새_토큰과_끊을_신원을_돌려준다():
    """G5"""
    interactor, calls = _run()
    result = await interactor.unlink(UnlinkIdentityCommand(user_id=5, provider="apple", auth_time=1_700_000_000))
    # generation 이 None 인 채로 issue 가 불린다 — revoke_all(세대를 올림) 이후 issue 가 "그 뒤" 세대를
    # 다시 읽는다는 뜻이다. 예전 세대를 들고 있다가 넘기면 방금 발급한 토큰이 곧장 무효가 된다.
    # 해제는 fresh_login 으로 발급하지 않고 요청 토큰의 로그인 시각을 그대로 물려준다 (해제를 되풀이해 늘릴 수 없게).
    assert calls == [
        "lock:5", "list_revocations:5", "delete:5:apple", "revoke_all:5",
        "issue:5:None:1700000000:False",
    ]
    assert result.identities == ("kakao",)
    assert result.tokens.refresh_token == "5.new-refresh"
    assert result.revocation == APPLE


async def test_마지막_로그인_수단은_해제할_수_없다():
    interactor, calls = _run(revocations=(KAKAO,))
    with pytest.raises(LastIdentityError):
        await interactor.unlink(UnlinkIdentityCommand(user_id=5, provider="kakao", auth_time=1_700_000_000))
    assert calls == ["lock:5", "list_revocations:5"]


async def test_연결되지_않은_수단은_IDENTITY_NOT_FOUND_다():
    interactor, calls = _run(revocations=(KAKAO, APPLE))
    with pytest.raises(IdentityNotFoundError):
        await interactor.unlink(UnlinkIdentityCommand(user_id=5, provider="google", auth_time=1_700_000_000))
    assert calls == ["lock:5", "list_revocations:5"]


async def test_모르는_제공자_이름은_거절한다():
    interactor, calls = _run()
    with pytest.raises(UnsupportedProviderError):
        await interactor.unlink(UnlinkIdentityCommand(user_id=5, provider="naver", auth_time=1_700_000_000))
    assert calls == []


async def test_잠근_뒤에_탈퇴한_유저면_아무것도_하지_않는다():
    interactor, calls = _run(user=_user(deleted=True))
    with pytest.raises(UserNotFoundError):
        await interactor.unlink(UnlinkIdentityCommand(user_id=5, provider="apple", auth_time=1_700_000_000))
    assert calls == ["lock:5"]


async def test_잠근_뒤에_보니_정지된_유저면_아무것도_하지_않는다():
    """요청 시작 때는 정지 전이었지만, 잠금을 얻는 사이 정지가 걸리면 잠근 뒤 다시 확인해 거절한다.
    거절하지 않으면 세션 전부를 폐기하고 방금 정지된 유저에게 새 토큰을 내주게 된다."""
    interactor, calls = _run(user=_user(suspended=True))
    with pytest.raises(AccountSuspendedError):
        await interactor.unlink(UnlinkIdentityCommand(user_id=5, provider="apple", auth_time=1_700_000_000))
    assert calls == ["lock:5"]
