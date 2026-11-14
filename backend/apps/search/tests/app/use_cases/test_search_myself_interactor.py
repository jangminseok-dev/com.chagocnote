from search.app.dtos.search_myself_dto import SearchMyselfQuery
from search.app.use_cases.search_myself_interactor import SearchMyselfInteractor


class _Record:
    def __init__(self):
        self.calls = []

    async def record(self, subject, note):
        self.calls.append((subject, note))


async def test_자기소개는_경로와_다루는_글과_제약을_적는다():
    record = _Record()
    response = await SearchMyselfInteractor(record).introduce_myself(SearchMyselfQuery(id=9, name="기록 검색 (search)"))
    assert (response.id, response.name) == (9, "기록 검색 (search)")
    for word in ("GET /v1/shops/{shop_id}/search", "care_note", "customer_memo", "2~100자", "semantic", "30줄",
                 "주의 고객 사유는 찾지 않습니다"):
        assert word in response.introduction
    assert record.calls == [("introduce_myself", "기록 검색 (search) 자기소개 조회")]
