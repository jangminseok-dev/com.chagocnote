from platform_admin.app.dtos.platform_myself_dto import PlatformMyselfQuery
from platform_admin.app.use_cases.platform_myself_interactor import PlatformMyselfInteractor


class _StubRecord:
    def __init__(self):
        self.records = []

    async def record(self, subject, note):
        self.records.append((subject, note))


async def test_운영자에게_실제_엔드포인트와_제약을_말하고_기록을_남긴다():
    """운영자 확인은 라우터의 require_operator 가드가 한다. 여기서 다시 하지 않는다."""
    record = _StubRecord()
    result = await PlatformMyselfInteractor(record).introduce_myself(
        PlatformMyselfQuery(id=3, name="플랫폼 운영 (platform_admin)")
    )
    assert result.id == 3
    assert "/v1/platform/shops" in result.introduction
    assert "운영자" in result.introduction
    assert record.records[0][0] == "introduce_myself"
