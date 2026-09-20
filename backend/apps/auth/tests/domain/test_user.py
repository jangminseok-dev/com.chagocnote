from datetime import datetime, timezone

from auth.domain.entities.user import User
from auth.domain.value_objects.provider import Provider


def _user(**overrides):
    base = dict(
        id=1, display_name="두부 보호자", profile_image_url=None, phone=None,
        suspended_at=None, deleted_at=None,
    )
    return User(**{**base, **overrides})


def test_정지_시각이_있으면_정지된_계정이다():
    assert _user().is_suspended is False
    assert _user(suspended_at=datetime.now(timezone.utc)).is_suspended is True


def test_삭제_시각이_있으면_탈퇴한_계정이다():
    assert _user().is_deleted is False
    assert _user(deleted_at=datetime.now(timezone.utc)).is_deleted is True


def test_제공자는_문자열_값으로_만들_수_있다():
    assert Provider("kakao") is Provider.KAKAO
    assert Provider.DEV.value == "dev"
