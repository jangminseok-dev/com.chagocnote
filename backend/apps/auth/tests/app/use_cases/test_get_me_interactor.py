import pytest

from auth.app.dtos.get_me_dto import GetMeQuery
from auth.app.use_cases.get_me_interactor import GetMeInteractor
from auth.domain.entities.social_identity import SocialIdentity
from auth.domain.entities.user import User
from auth.domain.errors import UserNotFoundError
from auth.domain.value_objects.provider import Provider


class _StubUsers:
    def __init__(self, user, identities=()):
        self.user = user
        self.identities = list(identities)

    async def get(self, user_id):
        return self.user

    async def list_identities(self, user_id):
        return self.identities


def _user():
    return User(id=5, display_name="두부 보호자", profile_image_url="https://img/1.jpg",
                phone=None, suspended_at=None, deleted_at=None)


async def test_프로필과_연결된_로그인_수단을_돌려준다():
    identities = [
        SocialIdentity(1, 5, Provider.KAKAO, "kakao-100", None),
        SocialIdentity(2, 5, Provider.APPLE, "apple-1", None),
    ]
    me = await GetMeInteractor(_StubUsers(_user(), identities)).get_me(GetMeQuery(user_id=5))
    assert (me.id, me.display_name, me.profile_image_url) == (5, "두부 보호자", "https://img/1.jpg")
    assert me.identities == ("kakao", "apple")


async def test_유저가_없으면_UserNotFoundError_다():
    with pytest.raises(UserNotFoundError):
        await GetMeInteractor(_StubUsers(None)).get_me(GetMeQuery(user_id=404))
