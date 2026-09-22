from customer.app.dtos.customer_myself_dto import CustomerMyselfQuery
from customer.app.use_cases.customer_myself_interactor import CustomerMyselfInteractor


class _StubRecord:
    def __init__(self):
        self.records = []

    async def record(self, subject, note):
        self.records.append((subject, note))


async def test_자기소개는_실제_엔드포인트와_제약을_말하고_기록을_남긴다():
    record = _StubRecord()
    result = await CustomerMyselfInteractor(record=record).introduce_myself(
        CustomerMyselfQuery(id=4, name="고객 (customer)")
    )
    assert result.id == 4
    for path in ("GET /customers", "/customers/lookup", "POST /customers/{customer_id}/pets",
                 "/pets/{pet_id}/passed-away", "/pet-condition-types"):
        assert path in result.introduction
    assert "customer:delete" in result.introduction and "익명화" in result.introduction
    assert record.records[0][0] == "introduce_myself"
