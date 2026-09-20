from auth.app.dtos.auth_myself_dto import AuthMyselfQuery
from auth.app.use_cases.auth_myself_interactor import AuthMyselfInteractor


class _StubRecord:
    def __init__(self):
        self.records = []

    async def record(self, subject, note):
        self.records.append((subject, note))


async def test_자기소개는_실제_엔드포인트와_제약을_말하고_기록을_남긴다():
    record = _StubRecord()
    result = await AuthMyselfInteractor(record=record).introduce_myself(
        AuthMyselfQuery(id=1, name="인증 (auth)")
    )
    assert result.id == 1
    assert "/v1/auth/social" in result.introduction
    assert "/v1/auth/refresh" in result.introduction
    assert "역할" in result.introduction
    assert record.records[0][0] == "introduce_myself"
