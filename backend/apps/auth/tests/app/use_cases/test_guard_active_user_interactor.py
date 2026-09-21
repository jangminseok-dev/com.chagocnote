from datetime import datetime, timezone

from auth.app.use_cases.guard_active_user_interactor import GuardActiveUserInteractor
from auth.domain.entities.user import User

NOW = datetime(2026, 9, 21, tzinfo=timezone.utc)


class _StubUsers:
    def __init__(self, user):
        self.user = user
        self.locked = []

    async def lock(self, user_id):
        self.locked.append(user_id)
        return self.user


def _user(suspended=False, deleted=False):
    return User(id=5, display_name="두부 보호자", profile_image_url=None, phone=None,
                suspended_at=NOW if suspended else None, deleted_at=NOW if deleted else None)


async def test_활동_중인_유저면_행을_잠그고_참을_돌려준다():
    users = _StubUsers(_user())
    assert await GuardActiveUserInteractor(users).lock_active(5) is True
    assert users.locked == [5]


async def test_탈퇴했거나_정지됐거나_없는_유저면_거짓이다():
    for user in (_user(deleted=True), _user(suspended=True), None):
        assert await GuardActiveUserInteractor(_StubUsers(user)).lock_active(5) is False
