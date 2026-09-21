from datetime import datetime, timezone

import pytest

from auth.app.dtos.grant_operator_dto import GrantOperatorCommand
from auth.app.use_cases.grant_operator_interactor import GrantOperatorInteractor
from auth.domain.entities.user import User
from auth.domain.errors import UserNotFoundError


class _StubUsers:
    def __init__(self, user):
        self.user = user
        self.locked_ids = []

    async def lock(self, user_id):
        self.locked_ids.append(user_id)
        return self.user


class _StubOperators:
    def __init__(self):
        self.granted = []

    async def grant(self, user_id):
        self.granted.append(user_id)


def _user(deleted_at=None):
    return User(id=5, display_name="운영자", profile_image_url=None, phone=None,
                suspended_at=None, deleted_at=deleted_at)


async def test_있는_유저를_운영자로_지정한다():
    operators, users = _StubOperators(), _StubUsers(_user())
    await GrantOperatorInteractor(users, operators).grant(GrantOperatorCommand(user_id=5))
    assert operators.granted == [5]
    assert users.locked_ids == [5]   # H4 — 겹친 탈퇴가 지나쳐 가지 않게 잠그고 읽는다


async def test_없는_유저는_지정하지_않는다():
    operators = _StubOperators()
    with pytest.raises(UserNotFoundError):
        await GrantOperatorInteractor(_StubUsers(None), operators).grant(GrantOperatorCommand(user_id=404))
    assert operators.granted == []


async def test_탈퇴한_유저는_지정하지_않는다():
    operators = _StubOperators()
    deleted = _user(deleted_at=datetime(2026, 9, 20, tzinfo=timezone.utc))
    with pytest.raises(UserNotFoundError):
        await GrantOperatorInteractor(_StubUsers(deleted), operators).grant(GrantOperatorCommand(user_id=5))
    assert operators.granted == []
