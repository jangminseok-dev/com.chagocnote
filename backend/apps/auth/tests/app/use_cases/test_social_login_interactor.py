from datetime import datetime, timezone

import pytest

from auth.app.dtos.social_login_dto import SocialLoginCommand
from auth.app.dtos.token_dto import TokenPair
from auth.app.use_cases.social_login_interactor import SocialLoginInteractor
from auth.domain.entities.user import User
from auth.domain.errors import AccountSuspendedError, IdentityAlreadyLinkedError, UnsupportedProviderError
from auth.domain.value_objects.provider import Provider
from auth.domain.value_objects.social_profile import SocialProfile


def _user(user_id=1, suspended=False):
    return User(
        id=user_id, display_name="두부 보호자", profile_image_url=None, phone=None,
        suspended_at=datetime.now(timezone.utc) if suspended else None, deleted_at=None,
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
    def __init__(self, existing=None, lost_race_to=None):
        self.existing = existing
        self.lost_race_to = lost_race_to   # 동시에 온 다른 요청이 먼저 만든 유저
        self.created = []
        self.filled = []

    async def find_by_identity(self, provider, provider_user_id):
        return self.existing

    async def create_with_identity(self, profile):
        if self.lost_race_to is not None:
            self.existing = self.lost_race_to
            raise IdentityAlreadyLinkedError("이미 연결된 계정입니다.")
        self.created.append(profile)
        return _user(user_id=77)

    async def fill_provider_refresh_token(self, provider, provider_user_id, token):
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


async def test_기존_유저가_제공자_토큰을_새로_받아_오면_비어_있는_자리를_채운다():
    users = _StubUsers(existing=_user(user_id=5))
    provider = _StubProvider(refresh_token="apple-refresh")
    await SocialLoginInteractor(_StubResolver(provider), users, _StubSessions()).login(_command())
    assert users.filled == [(Provider.KAKAO, "kakao-100", "apple-refresh")]


async def test_제공자_토큰이_없으면_채우지_않는다():
    users = _StubUsers(existing=_user(user_id=5))
    await SocialLoginInteractor(_StubResolver(_StubProvider()), users, _StubSessions()).login(_command())
    assert users.filled == []
