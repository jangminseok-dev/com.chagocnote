from datetime import datetime, timezone

import pytest

from auth.app.dtos.link_identity_dto import LinkIdentityCommand
from auth.app.use_cases.link_identity_interactor import LinkIdentityInteractor
from auth.domain.entities.social_identity import SocialIdentity
from auth.domain.entities.user import User
from auth.domain.errors import (
    IdentityAlreadyLinkedError,
    UnsupportedProviderError,
    UserNotFoundError,
)
from auth.domain.value_objects.provider import Provider
from auth.domain.value_objects.social_profile import SocialProfile


def _user(deleted=False):
    return User(id=5, display_name="두부 보호자", profile_image_url=None, phone=None, suspended_at=None,
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

    def resolve(self, provider):
        return self.provider


class _StubUsers:
    def __init__(self, calls, user, taken=False):
        self.calls = calls
        self.user = user
        self.taken = taken
        self.added = []

    async def lock(self, user_id):
        self.calls.append("lock")
        return self.user

    async def add_identity(self, user_id, profile):
        if self.taken:
            raise IdentityAlreadyLinkedError("이미 다른 계정에 연결된 로그인 수단입니다.")
        self.added.append((user_id, profile.provider, profile.provider_user_id))

    async def list_identities(self, user_id):
        return [SocialIdentity(1, 5, Provider.KAKAO, "kakao-100", None),
                SocialIdentity(2, 5, Provider.APPLE, "apple-1", None)]


def _command(provider="apple"):
    return LinkIdentityCommand(user_id=5, provider=provider, token="apple-id-token",
                               authorization_code="auth-code", nonce="raw-nonce")


def _run(user=None, taken=False):
    calls = []
    provider, users = _StubProvider(calls), _StubUsers(calls, user if user is not None else _user(), taken)
    return LinkIdentityInteractor(_StubResolver(provider), users), provider, users, calls


async def test_제공자가_확인해_준_신원을_붙이고_수단_목록을_돌려준다():
    interactor, provider, users, _ = _run()
    result = await interactor.link(_command())
    assert users.added == [(5, Provider.APPLE, "apple-1")]
    assert result.identities == ("kakao", "apple")
    seen = provider.seen[0]
    assert (seen.token, seen.authorization_code, seen.nonce) == ("apple-id-token", "auth-code", "raw-nonce")


async def test_제공자_검증은_유저_행을_잠그기_전에_끝낸다():
    """잠금을 쥔 채 외부 HTTP 를 부르지 않는다."""
    interactor, _, _, calls = _run()
    await interactor.link(_command())
    assert calls == ["verify", "lock"]


async def test_잠근_뒤에_탈퇴한_유저면_붙이지_않는다():
    """G2 — 탈퇴와 겹친 연결이 탈퇴한 유저에 신원을 남기지 않는다."""
    interactor, _, users, _ = _run(user=_user(deleted=True))
    with pytest.raises(UserNotFoundError):
        await interactor.link(_command())
    assert users.added == []


async def test_다른_계정에_붙어_있는_신원은_거절한다():
    """G3"""
    interactor, _, _, _ = _run(taken=True)
    with pytest.raises(IdentityAlreadyLinkedError):
        await interactor.link(_command())


async def test_모르는_제공자_이름은_거절한다():
    interactor, _, _, calls = _run()
    with pytest.raises(UnsupportedProviderError):
        await interactor.link(_command(provider="naver"))
    assert calls == []
