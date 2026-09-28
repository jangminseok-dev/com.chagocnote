from visit.app.dtos.visit_myself_dto import VisitMyselfQuery
from visit.app.use_cases.visit_myself_interactor import VisitMyselfInteractor


class _Record:
    def __init__(self):
        self.calls = []

    async def record(self, subject, note):
        self.calls.append((subject, note))


async def test_자기소개는_묶음의_경로와_권한을_적는다():
    record = _Record()
    result = await VisitMyselfInteractor(record).introduce_myself(VisitMyselfQuery(id=5, name="방문 (visit)"))
    assert (result.id, result.name) == (5, "방문 (visit)")
    for words in ("POST /visits/transitions", "reservation:write", "shop:update", "/visit-settings", "10분 단위",
                  "PUT /visits/{visit_id}/record", "sales:write", "RECORD_VERSION_CONFLICT",
                  "POST /visits/{visit_id}/record/media", "record:delete", "GET·PUT /report-settings",
                  "GET /visits/{visit_id}/report", "PUT /visits/{visit_id}/report",
                  "DELETE /visits/{visit_id}/report", "REPORT_EMPTY", "VISIT_REPORT_SENT", "report_sent",
                  "GET /v1/public/report", "POST /v1/public/report/viewed", "X-Report-Token"):
        assert words in result.introduction
    assert record.calls == [("introduce_myself", "방문 (visit) 자기소개 조회")]
