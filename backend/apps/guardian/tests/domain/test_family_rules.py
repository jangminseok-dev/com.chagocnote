"""가족 초대의 규칙(⑫) — 코드 모양·해시·기간, 가족 수의 범위."""
from datetime import datetime, timedelta, timezone

import pytest

from guardian.domain.entities.family_invite import FamilyInvite
from guardian.domain.errors import GuardianInputError
from guardian.domain.services.family_rules import (
    check_family_max, hash_code, invite_expires_at, is_code_shaped, new_invite_code,
)

NOW = datetime(2026, 11, 16, 3, tzinfo=timezone.utc)


def test_초대_코드는_43자이고_해시만_남긴다():
    code = new_invite_code()

    assert is_code_shaped(code) and len(hash_code(code)) == 64 and hash_code(code) != code
    assert new_invite_code() != code
    assert not is_code_shaped(None) and not is_code_shaped("x" * 42) and not is_code_shaped("x" * 42 + "!")


def test_초대는_24시간_한_번만이고_죽이면_못_쓴다():
    invite = FamilyInvite(id=1, link_id=2, created_at=NOW, expires_at=invite_expires_at(NOW), used_at=None, revoked_at=None)

    assert invite.expires_at - NOW == timedelta(hours=24)
    assert invite.is_usable(NOW + timedelta(hours=23, minutes=59))
    assert not invite.is_usable(invite.expires_at)
    assert not FamilyInvite(**{**invite.__dict__, "used_at": NOW}).is_usable(NOW)
    assert not FamilyInvite(**{**invite.__dict__, "revoked_at": NOW}).is_usable(NOW)


@pytest.mark.parametrize("value", [-1, 11])
def test_가족_수는_0에서_10_사이다(value):
    check_family_max(0)
    check_family_max(10)
    with pytest.raises(GuardianInputError):
        check_family_max(value)
