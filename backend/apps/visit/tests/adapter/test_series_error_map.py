"""반복 묶음 오류의 코드·상태와 details(⑭)."""
from visit.adapter.inbound.api.error_map import VISIT_ERROR_STATUS
from visit.domain.errors import VisitSeriesConflictError, VisitSeriesNotFoundError
from visit.domain.services.visit_series import OUT_OF_RANGE, TAKEN, SeriesConflict
from visit.tests.helpers.builders import TZ, kst


def test_묶음_오류의_코드와_상태():
    assert (VisitSeriesNotFoundError.code, VISIT_ERROR_STATUS[VisitSeriesNotFoundError]) == (
        "VISIT_SERIES_NOT_FOUND", 404)
    assert (VisitSeriesConflictError.code, VISIT_ERROR_STATUS[VisitSeriesConflictError]) == (
        "VISIT_SERIES_CONFLICT", 409)


def test_걸린_회차는_방문_아이_매장_시간대의_시각_사유만_싣는다():
    error = VisitSeriesConflictError(
        [SeriesConflict(3, 101, kst(12, 18, 14), TAKEN), SeriesConflict(4, None, kst(12, 25, 14), OUT_OF_RANGE)], TZ)
    assert error.details == {"conflicts": [
        {"visit_id": 3, "pet_id": 101, "starts_at": "2026-12-18T14:00:00+09:00", "reason": "taken"},
        {"visit_id": 4, "pet_id": None, "starts_at": "2026-12-25T14:00:00+09:00", "reason": "out_of_range"},
    ]}
    assert str(error) == "이미 예약이 있거나 잡을 수 없는 회차가 있어요."
