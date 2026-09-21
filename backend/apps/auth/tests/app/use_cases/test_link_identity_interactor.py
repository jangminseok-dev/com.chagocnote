from datetime import datetime, timezone

import pytest

from auth.app.dtos.link_identity_dto import LinkIdentityCommand
from auth.app.use_cases.link_identity_interactor import LinkIdentityInteractor
from auth.domain.entities.social_identity import SocialIdentity
from auth.domain.entities.user import User
from auth.domain.errors import (
    AccountSuspendedError,
    IdentityAlreadyLinkedError,
    UnsupportedProviderError,
    UserNotFoundError,
)
from auth.domain.value_objects.provider import Provider
from auth.domain.value_objects.social_profile import SocialProfile


def _user(deleted=False, suspended=False):
    return User(id=5, display_name="두부 보호자", profile_image_url=None, phone=None,
                suspended_at=datetime.now(timezone.utc) if suspended else None,
                deleted_at=datetime.now(timezone.utc) if deleted else None)


class _StubProvider:
    def __init__(self, calls):
        self.calls = calls
        self.seen = []

    async def verify(self, credentials):
        self.calls.append("verify")
        self.seen.append(credentials)
        return SocialProfile(Provider.APPLE, "apple-1", None, None, None, "apple-refresh")


class _StubResolver:
    def __init__(self, provider):
        self.provider = provider
        self.seen = []

    def resolve(self, provider):
        self.seen.append(provider)
        return self.provider


class _StubUsers:
    def __init__(self, calls, user, taken=False):
        self.calls = calls
        self.user = user
        self.taken = taken
        self.added = []
        self.locked_user_id = None
        self.listed_user_id = None

    async def lock(self, user_id):
        self.calls.append("lock")
        self.locked_user_id = user_id
        return self.user

    async def add_identity(self, user_id, profile):
        if self.taken:
            raise IdentityAlreadyLinkedError("이미 다른 계정에 연결된 로그인 수단입니다.")
        self.added.append((user_id, profile.provider, profile.provider_user_id))

    async def list_identities(self, user_id):
        self.listed_user_id = user_id
        return [SocialIdentity(1, 5, Provider.KAKAO, "kakao-100", None),
                SocialIdentity(2, 5, Provider.APPLE, "apple-1", None)]


def _command(provider="apple"):
    return LinkIdentityCommand(user_id=5, provider=provider, token="apple-id-token",
                               authorization_code="auth-code", nonce="raw-nonce")


def _run(user=None, taken=False):
    calls = []
    provider, users = _StubProvider(calls), _StubUsers(calls, user if user is not None else _user(), taken)
    resolver = _StubResolver(provider)
    return LinkIdentityInteractor(resolver, users), provider, users, resolver, calls


async def test_제공자가_확인해_준_신원을_붙이고_수단_목록을_돌려준다():
    interactor, provider, users, resolver, _ = _run()
    result = await interactor.link(_command())
    assert users.added == [(5, Provider.APPLE, "apple-1")]
    assert result.identities == ("kakao", "apple")
    seen = provider.seen[0]
    assert (seen.token, seen.authorization_code, seen.nonce) == ("apple-id-token", "auth-code", "raw-nonce")
    assert resolver.seen == [Provider.APPLE]
    assert (users.locked_user_id, users.listed_user_id) == (5, 5)


async def test_제공자_검증은_유저_행을_잠그기_전에_끝낸다():
    """잠금을 쥔 채 외부 HTTP 를 부르지 않는다."""
    interactor, _, _, _, calls = _run()
    await interactor.link(_command())
    assert calls == ["verify", "lock"]


async def test_잠근_뒤에_탈퇴한_유저면_붙이지_않는다():
    """G2 — 탈퇴와 겹친 연결이 탈퇴한 유저에 신원을 남기지 않는다."""
    interactor, _, users, _, _ = _run(user=_user(deleted=True))
    with pytest.raises(UserNotFoundError):
        await interactor.link(_command())
    assert users.added == []


async def test_잠근_뒤에_정지된_유저면_붙이지_않는다():
    """요청 시작 때는 정지 전이었지만, 제공자 왕복(최대 5초) 동안 정지가 걸리면
    잠금 뒤 다시 확인해 거절한다."""
    interactor, _, users, _, _ = _run(user=_user(suspended=True))
    with pytest.raises(AccountSuspendedError):
        await interactor.link(_command())
    assert users.added == []


async def test_다른_계정에_붙어_있는_신원은_거절한다():
    """G3"""
    interactor, _, _, _, _ = _run(taken=True)
    with pytest.raises(IdentityAlreadyLinkedError):
        await interactor.link(_command())


async def test_모르는_제공자_이름은_거절한다():
    interactor, _, _, _, calls = _run()
    with pytest.raises(UnsupportedProviderError):
        await interactor.link(_command(provider="naver"))
    assert calls == []
