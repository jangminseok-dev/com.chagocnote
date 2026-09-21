import pytest

from platform_admin.app.dtos.platform_myself_dto import PlatformMyselfQuery
from platform_admin.app.use_cases.platform_myself_interactor import PlatformMyselfInteractor
from platform_admin.domain.errors import NotAnOperatorError


class _StubRecord:
    def __init__(self):
        self.records = []

    async def record(self, subject, note):
        self.records.append((subject, note))


class _StubOperators:
    def __init__(self, operator_ids):
        self.operator_ids = set(operator_ids)

    async def is_operator(self, user_id):
        return user_id in self.operator_ids


def _query(user_id):
    return PlatformMyselfQuery(id=3, name="플랫폼 운영 (platform_admin)", user_id=user_id)


async def test_운영자에게_실제_엔드포인트와_제약을_말하고_기록을_남긴다():
    record = _StubRecord()
    result = await PlatformMyselfInteractor(record, _StubOperators([5])).introduce_myself(_query(5))
    assert result.id == 3
    assert "/v1/platform/shops" in result.introduction
    assert "운영자" in result.introduction
    assert record.records[0][0] == "introduce_myself"


async def test_운영자가_아니면_거절하고_기록하지_않는다():
    record = _StubRecord()
    with pytest.raises(NotAnOperatorError):
        await PlatformMyselfInteractor(record, _StubOperators([5])).introduce_myself(_query(6))
    assert record.records == []
