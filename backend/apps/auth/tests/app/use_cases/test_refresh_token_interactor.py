from datetime import datetime, timezone

import pytest

from auth.app.dtos.refresh_token_dto import RefreshTokenCommand
from auth.app.dtos.token_dto import TokenPair
from auth.app.use_cases.refresh_token_interactor import RefreshTokenInteractor
from auth.domain.entities.user import User
from auth.domain.errors import (
    AccountSuspendedError,
    InvalidRefreshTokenError,
    RefreshTokenReuseError,
)
from auth.domain.value_objects.refresh_lookup import RefreshLookup, RefreshStatus


def _user(suspended=False, deleted=False):
    now = datetime.now(timezone.utc)
    return User(id=5, display_name="두부 보호자", profile_image_url=None, phone=None,
                suspended_at=now if suspended else None, deleted_at=now if deleted else None)


class _StubStore:
    def __init__(self, lookup):
        self.lookup = lookup
        self.revoked_all = []

    async def take(self, token):
        return self.lookup

    async def revoke_all(self, user_id):
        self.revoked_all.append(user_id)


class _StubUsers:
    def __init__(self, user):
        self.user = user

    async def get(self, user_id):
        return self.user


class _StubSessions:
    def __init__(self):
        self.issued_for = []
        self.login_marks = []

    async def issue(self, user_id, generation=None, *, auth_time=None, fresh_login=False):
        self.issued_for.append((user_id, generation))
        self.login_marks.append((auth_time, fresh_login))
        return TokenPair("new-access", "new-refresh", 900)


def _run(lookup, user=None):
    store, sessions = _StubStore(lookup), _StubSessions()
    interactor = RefreshTokenInteractor(store, _StubUsers(user), sessions)
    return interactor, store, sessions


async def test_유효한_토큰이면_꺼낼_때의_세대로_새_토큰_한_쌍을_발급한다():
    interactor, _, sessions = _run(RefreshLookup(RefreshStatus.ACTIVE, 5, 4), _user())
    pair = await interactor.refresh(RefreshTokenCommand("5.old-refresh"))
    assert pair.refresh_token == "new-refresh"
    assert sessions.issued_for == [(5, 4)]


async def test_모르는_토큰은_거절한다():
    interactor, store, sessions = _run(RefreshLookup(RefreshStatus.MISSING, None))
    with pytest.raises(InvalidRefreshTokenError):
        await interactor.refresh(RefreshTokenCommand("unknown"))
    assert store.revoked_all == [] and sessions.issued_for == []


async def test_이미_쓴_토큰이_다시_오면_그_유저의_세션을_모두_폐기한다():
    interactor, store, sessions = _run(RefreshLookup(RefreshStatus.USED, 5), _user())
    with pytest.raises(RefreshTokenReuseError):
        await interactor.refresh(RefreshTokenCommand("stolen"))
    assert store.revoked_all == [5]
    assert sessions.issued_for == []


async def test_탈퇴했거나_없는_유저에게는_발급하지_않는다():
    for user in (None, _user(deleted=True)):
        interactor, _, sessions = _run(RefreshLookup(RefreshStatus.ACTIVE, 5), user)
        with pytest.raises(InvalidRefreshTokenError):
            await interactor.refresh(RefreshTokenCommand("old-refresh"))
        assert sessions.issued_for == []


async def test_정지된_유저에게는_발급하지_않는다():
    interactor, _, sessions = _run(RefreshLookup(RefreshStatus.ACTIVE, 5), _user(suspended=True))
    with pytest.raises(AccountSuspendedError):
        await interactor.refresh(RefreshTokenCommand("old-refresh"))
    assert sessions.issued_for == []


async def test_갱신은_로그인_시각을_찍지_않는다():
    interactor, _, sessions = _run(RefreshLookup(RefreshStatus.ACTIVE, 5, 4), _user())
    await interactor.refresh(RefreshTokenCommand("5.old-refresh"))
    assert sessions.login_marks == [(None, False)]
