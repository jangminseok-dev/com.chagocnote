import pytest

from visit.adapter.inbound.api.error_map import VISIT_ERROR_STATUS
from visit.domain.errors import (
    ReportClosedError,
    ReportEmptyError,
    ReportNotFoundError,
    VisitNotCompletedError,
    VisitReportSentError,
)


@pytest.mark.parametrize(("error", "code", "status"), [
    (ReportNotFoundError, "REPORT_NOT_FOUND", 404),
    (ReportClosedError, "REPORT_CLOSED", 410),
    (ReportEmptyError, "REPORT_EMPTY", 422),
    (VisitNotCompletedError, "VISIT_NOT_COMPLETED", 409),
    (VisitReportSentError, "VISIT_REPORT_SENT", 409),
])
def test_알림장_오류의_코드와_상태(error, code, status):
    assert error.code == code
    assert VISIT_ERROR_STATUS[error] == status
