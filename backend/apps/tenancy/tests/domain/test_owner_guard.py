import pytest

from tenancy.domain.errors import LastOwnerError
from tenancy.domain.services.owner_guard import ensure_owner_remains


def test_사장이_한_명뿐이면_LAST_OWNER_다():
    with pytest.raises(LastOwnerError):
        ensure_owner_remains(owner_count=1)


def test_사장이_둘_이상이면_통과한다():
    ensure_owner_remains(owner_count=2)
