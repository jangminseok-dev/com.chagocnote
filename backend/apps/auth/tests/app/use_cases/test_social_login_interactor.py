from datetime import datetime, timezone

import pytest

from auth.app.dtos.social_login_dto import SocialLoginCommand
from auth.app.dtos.token_dto import TokenPair
from auth.app.use_cases.social_login_interactor import SocialLoginInteractor
from auth.domain.entities.user import User
from auth.domain.errors import (
    AccountSuspendedError,
    IdentityAlreadyLinkedError,
    UnsupportedProviderError,
    UserNotFoundError,
)
from auth.domain.value_objects.provider import Provider
from auth.domain.value_objects.social_profile import SocialProfile


def _user(user_id=1, suspended=False, deleted=False):
    now = datetime.now(timezone.utc)
    return User(
        id=user_id, display_name="두부 보호자", profile_image_url=None, phone=None,
        suspended_at=now if suspended else None, deleted_at=now if deleted else None,
    )


class _StubProvider:
    def __init__(self, refresh_token=None):
        self.refresh_token = refresh_token
        self.seen = []

    async def verify(self, credentials):
        self.seen.append(credentials)
        return SocialProfile(Provider.KAKAO, "kakao-100", None, "두부 보호자", None, self.refresh_token)


class _StubResolver:
    def __init__(self, provider):
        self._provider = provider

    def resolve(self, provider):
        return self._provider


class _StubUsers:
    """호출 순서와 인자를 기록한다.

    finds 를 주면 find_by_identity 가 그 값을 차례로 돌려준다(잠금 뒤 재조회가 어긋나는 상황).
    다 쓰면 existing 으로 돌아간다. locked 를 주면 lock 이 그 값을 돌려준다.
    """

    def __init__(self, existing=None, lost_race_to=None, finds=None, locked=None):
        self.existing = existing
        self.lost_race_to = lost_race_to   # 동시에 온 다른 요청이 먼저 만든 유저
        self.finds = list(finds) if finds is not None else None
        self.locked = locked
        self.created = []
        self.filled = []
        self.calls = []                    # 호출 순서
        self.locked_ids = []

    async def find_by_identity(self, provider, provider_user_id):
        self.calls.append("find")
        if self.finds:
            return self.finds.pop(0)
        return self.existing

    async def create_with_identity(self, profile):
        self.calls.append("create")
        if self.lost_race_to is not None:
            self.existing = self.lost_race_to
            raise IdentityAlreadyLinkedError("이미 연결된 계정입니다.")
        self.created.append(profile)
        return _user(user_id=77)

    async def lock(self, user_id):
        self.calls.append("lock")
        self.locked_ids.append(user_id)
        if self.locked is not None:
            return self.locked
        return self.existing if self.existing is not None else _user(user_id=user_id)

    async def fill_provider_refresh_token(self, provider, provider_user_id, token):
        self.calls.append("fill")
        self.filled.append((provider, provider_user_id, token))


class _StubSessions:
    def __init__(self):
        self.issued_for = []

    async def issue(self, user_id):
        self.issued_for.append(user_id)
        return TokenPair("access", "refresh", 900)


def _command(provider="kakao"):
    return SocialLoginCommand(provider=provider, token="provider-token",
                              authorization_code=None, nonce=None, display_name=None)


async def test_처음_보는_신원이면_유저를_만들고_토큰을_발급한다():
    users, sessions = _StubUsers(existing=None), _StubSessions()
    result = await SocialLoginInteractor(_StubResolver(_StubProvider()), users, sessions).login(_command())
    assert (result.user_id, result.is_new_user) == (77, True)
    assert len(users.created) == 1
    assert sessions.issued_for == [77]
    assert result.tokens.refresh_token == "refresh"
    assert "lock" not in users.calls   # 방금 만든 행은 아직 남에게 보이지 않아 잠글 것이 없다


async def test_이미_있는_신원이면_새로_만들지_않는다():
    users, sessions = _StubUsers(existing=_user(user_id=5)), _StubSessions()
    result = await SocialLoginInteractor(_StubResolver(_StubProvider()), users, sessions).login(_command())
    assert (result.user_id, result.is_new_user) == (5, False)
    assert users.created == []


async def test_앱이_보낸_토큰을_제공자_검증에_그대로_넘긴다():
    provider = _StubProvider()
    await SocialLoginInteractor(_StubResolver(provider), _StubUsers(), _StubSessions()).login(_command())
    assert provider.seen[0].token == "provider-token"


async def test_정지된_계정에는_토큰을_발급하지_않는다():
    users, sessions = _StubUsers(existing=_user(suspended=True)), _StubSessions()
    with pytest.raises(AccountSuspendedError):
        await SocialLoginInteractor(_StubResolver(_StubProvider()), users, sessions).login(_command())
    assert sessions.issued_for == []


async def test_모르는_제공자_이름은_거절한다():
    with pytest.raises(UnsupportedProviderError):
        await SocialLoginInteractor(
            _StubResolver(_StubProvider()), _StubUsers(), _StubSessions()
        ).login(_command(provider="naver"))


async def test_동시에_온_첫_로그인에서_진_쪽은_먼저_만들어진_유저로_로그인한다():
    """C1"""
    users, sessions = _StubUsers(lost_race_to=_user(user_id=5)), _StubSessions()
    result = await SocialLoginInteractor(_StubResolver(_StubProvider()), users, sessions).login(_command())
    assert (result.user_id, result.is_new_user) == (5, False)
    assert sessions.issued_for == [5]
    # 진 쪽도 기존 유저 경로와 같이 잠그고 다시 본다.
    assert users.calls == ["find", "create", "find", "lock", "find"]


async def test_기존_유저가_제공자_토큰을_새로_받아_오면_비어_있는_자리를_채운다():
    users = _StubUsers(existing=_user(user_id=5))
    provider = _StubProvider(refresh_token="apple-refresh")
    await SocialLoginInteractor(_StubResolver(provider), users, _StubSessions()).login(_command())
    assert users.filled == [(Provider.KAKAO, "kakao-100", "apple-refresh")]


async def test_제공자_토큰이_없으면_채우지_않는다():
    users = _StubUsers(existing=_user(user_id=5))
    await SocialLoginInteractor(_StubResolver(_StubProvider()), users, _StubSessions()).login(_command())
    assert users.filled == []


async def test_기존_유저에게_발급하기_전에_유저_행을_잠그고_신원을_다시_본다():
    """F-I1 — 제공자 검증(외부 HTTP)은 잠금 앞, 신원 재조회는 잠금 뒤다."""
    users, sessions = _StubUsers(existing=_user(user_id=5)), _StubSessions()
    await SocialLoginInteractor(_StubResolver(_StubProvider()), users, sessions).login(_command())
    assert users.calls == ["find", "lock", "find"]
    assert users.locked_ids == [5]
    assert sessions.issued_for == [5]


async def test_제공자_토큰은_잠근_뒤에_채운다():
    """F-I1 Apple 변형 — 잠금 없이 부르면 해제가 지운 신원을 기다렸다가 0행으로 끝난 뒤 발급하게 된다."""
    users = _StubUsers(existing=_user(user_id=5))
    provider = _StubProvider(refresh_token="apple-refresh")
    await SocialLoginInteractor(_StubResolver(provider), users, _StubSessions()).login(_command())
    assert users.calls == ["find", "lock", "find", "fill"]


async def test_잠근_뒤에_정지된_유저면_발급하지_않는다():
    """잠금을 얻는 사이에 정지가 걸렸다. 정지 여부는 잠근 뒤의 값으로 판단한다."""
    users, sessions = (
        _StubUsers(existing=_user(user_id=5), locked=_user(user_id=5, suspended=True)),
        _StubSessions(),
    )
    with pytest.raises(AccountSuspendedError):
        await SocialLoginInteractor(_StubResolver(_StubProvider()), users, sessions).login(_command())
    assert sessions.issued_for == []


async def test_잠근_뒤에_탈퇴한_유저면_발급하지_않는다():
    users, sessions = (
        _StubUsers(existing=_user(user_id=5), locked=_user(user_id=5, deleted=True)),
        _StubSessions(),
    )
    with pytest.raises(UserNotFoundError):
        await SocialLoginInteractor(_StubResolver(_StubProvider()), users, sessions).login(_command())
    assert sessions.issued_for == []


async def test_잠근_뒤에_신원이_사라졌으면_새_가입으로_간다():
    """해제가 그 사이 커밋됐다 — 해제된 수단은 빈 새 계정이 된다."""
    users, sessions = (
        _StubUsers(existing=None, finds=[_user(user_id=5), None, None]),
        _StubSessions(),
    )
    result = await SocialLoginInteractor(_StubResolver(_StubProvider()), users, sessions).login(_command())
    assert (result.user_id, result.is_new_user) == (77, True)
    assert users.calls == ["find", "lock", "find", "find", "create"]
    assert sessions.issued_for == [77]


async def test_잠근_뒤에_신원이_다른_유저로_옮겨_갔으면_그_유저로_다시_조회한다():
    moved = _user(user_id=9)
    users, sessions = (
        _StubUsers(existing=moved, finds=[_user(user_id=5), moved]),
        _StubSessions(),
    )
    result = await SocialLoginInteractor(_StubResolver(_StubProvider()), users, sessions).login(_command())
    assert result.user_id == 9
    assert users.locked_ids == [5, 9]
    assert sessions.issued_for == [9]


async def test_두_번_어긋나면_토큰을_발급하지_않는다():
    """무한 루프를 돌지 않는다. 두 번째에도 어긋나면 다시 로그인하라고 끝낸다."""
    users, sessions = (
        _StubUsers(existing=None, finds=[_user(user_id=5), None, _user(user_id=5), None]),
        _StubSessions(),
    )
    with pytest.raises(UserNotFoundError):
        await SocialLoginInteractor(_StubResolver(_StubProvider()), users, sessions).login(_command())
    assert sessions.issued_for == []
    assert users.created == []
