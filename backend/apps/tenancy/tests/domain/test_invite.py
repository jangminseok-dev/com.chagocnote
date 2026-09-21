from datetime import datetime, timedelta, timezone

import pytest

from tenancy.domain.entities.invite import Invite
from tenancy.domain.errors import InviteExhaustedError, InviteExpiredError, InviteInvalidError
from tenancy.domain.value_objects.role_code import RoleCode

NOW = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)


def _invite(**overrides):
    base = dict(id=1, shop_id=1, role=RoleCode.STAFF, expires_at=NOW + timedelta(days=7),
                max_uses=1, used_count=0, revoked_at=None)
    return Invite(**{**base, **overrides})


def test_기한_안이고_횟수가_남았으면_쓸_수_있다():
    _invite().ensure_usable(NOW)


def test_만료_시각이_되면_INVITE_EXPIRED_다():
    with pytest.raises(InviteExpiredError):
        _invite(expires_at=NOW).ensure_usable(NOW)


def test_사용_횟수를_다_쓰면_INVITE_EXHAUSTED_다():
    with pytest.raises(InviteExhaustedError):
        _invite(used_count=1).ensure_usable(NOW)


def test_무효화된_초대는_INVITE_INVALID_다():
    with pytest.raises(InviteInvalidError):
        _invite(revoked_at=NOW - timedelta(hours=1)).ensure_usable(NOW)
