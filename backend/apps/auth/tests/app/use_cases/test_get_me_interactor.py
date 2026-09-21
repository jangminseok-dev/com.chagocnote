import pytest

from auth.app.dtos.get_me_dto import GetMeQuery
from auth.app.use_cases.get_me_interactor import GetMeInteractor
from auth.domain.entities.social_identity import SocialIdentity
from auth.domain.entities.user import User
from auth.domain.errors import UserNotFoundError
from auth.domain.value_objects.provider import Provider
from hub.app.dtos.membership_summary import MembershipSummary


class _StubUsers:
    def __init__(self, user, identities=()):
        self.user = user
        self.identities = list(identities)

    async def get(self, user_id):
        return self.user

    async def list_identities(self, user_id):
        return self.identities


class _StubMemberships:
    def __init__(self, shops=()):
        self.shops = list(shops)
        self.calls = []

    async def list_for_user(self, user_id):
        self.calls.append(user_id)
        return self.shops


def _user():
    return User(id=5, display_name="두부 보호자", profile_image_url="https://img/1.jpg",
                phone=None, suspended_at=None, deleted_at=None)


async def test_프로필과_연결된_로그인_수단과_소속_매장을_돌려준다():
    identities = [
        SocialIdentity(1, 5, Provider.KAKAO, "kakao-100", None),
        SocialIdentity(2, 5, Provider.APPLE, "apple-1", None),
    ]
    memberships = _StubMemberships([MembershipSummary(shop_id=3, shop_name="Hiss Haus", role="owner")])
    me = await GetMeInteractor(_StubUsers(_user(), identities), memberships).get_me(GetMeQuery(user_id=5))
    assert (me.id, me.display_name, me.profile_image_url) == (5, "두부 보호자", "https://img/1.jpg")
    assert me.identities == ("kakao", "apple")
    assert me.shops == (MembershipSummary(shop_id=3, shop_name="Hiss Haus", role="owner"),)
    assert memberships.calls == [5]


async def test_소속이_없으면_매장_목록이_비어_있다():
    me = await GetMeInteractor(_StubUsers(_user()), _StubMemberships()).get_me(GetMeQuery(user_id=5))
    assert me.shops == ()


async def test_유저가_없으면_UserNotFoundError_다():
    with pytest.raises(UserNotFoundError):
        await GetMeInteractor(_StubUsers(None), _StubMemberships()).get_me(GetMeQuery(user_id=404))
