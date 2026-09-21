from auth.app.use_cases.get_user_profiles_interactor import GetUserProfilesInteractor
from auth.domain.entities.user import User
from hub.app.dtos.user_profile import UserProfile


class _StubUsers:
    def __init__(self, users):
        self.users = users
        self.calls = []

    async def list_by_ids(self, user_ids):
        self.calls.append(list(user_ids))
        return self.users


def _user(user_id, name, image=None):
    return User(id=user_id, display_name=name, profile_image_url=image, phone="010-0000-0000",
                suspended_at=None, deleted_at=None)


async def test_유저_ID_로_프로필을_묶어_돌려준다():
    users = _StubUsers([_user(1, "사장님", "https://img/1.jpg"), _user(2, "직원")])
    profiles = await GetUserProfilesInteractor(users).get_profiles([1, 2])
    assert profiles == {
        1: UserProfile(user_id=1, display_name="사장님", profile_image_url="https://img/1.jpg"),
        2: UserProfile(user_id=2, display_name="직원", profile_image_url=None),
    }
    assert users.calls == [[1, 2]]
