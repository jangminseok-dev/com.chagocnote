import pytest

from auth.domain.errors import LastIdentityError
from auth.domain.services.identity_guard import ensure_identity_remains


def test_로그인_수단이_하나뿐이면_해제할_수_없다():
    with pytest.raises(LastIdentityError):
        ensure_identity_remains(identity_count=1)


def test_둘_이상이면_해제할_수_있다():
    ensure_identity_remains(identity_count=2)
