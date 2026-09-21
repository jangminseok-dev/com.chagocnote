from tenancy.app.dtos.tenancy_myself_dto import TenancyMyselfQuery
from tenancy.app.use_cases.tenancy_myself_interactor import TenancyMyselfInteractor


class _StubRecord:
    def __init__(self):
        self.records = []

    async def record(self, subject, note):
        self.records.append((subject, note))


async def test_자기소개는_실제_엔드포인트와_제약을_말하고_기록을_남긴다():
    record = _StubRecord()
    result = await TenancyMyselfInteractor(record=record).introduce_myself(
        TenancyMyselfQuery(id=2, name="매장 (tenancy)")
    )
    assert result.id == 2
    assert "/v1/invites/accept" in result.introduction
    assert "/v1/shops/{shop_id}/members" in result.introduction
    assert "사장" in result.introduction
    assert record.records[0][0] == "introduce_myself"
