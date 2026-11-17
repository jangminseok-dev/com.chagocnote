from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

if TYPE_CHECKING:   # visit_series 가 visit_schedule → errors 를 import 하므로 실행 때는 읽지 않는다
    from visit.domain.services.visit_series import SeriesConflict


class VisitError(Exception):
    """visit 도메인 오류의 바탕. code 는 응답 본문의 code 로 나간다."""

    code = "VISIT_ERROR"


class VisitInputError(VisitError):
    """형식은 맞지만 규칙에 어긋난 입력(10분 단위가 아닌 시각, 예약 가능 범위 밖, 취소 사유 누락). 422 다."""

    code = "VALIDATION_ERROR"


class VisitNotFoundError(VisitError):
    code = "VISIT_NOT_FOUND"


class VisitStateConflictError(VisitError):
    """지금 상태에서 할 수 없는 행동. 다른 기기가 먼저 상태를 바꾼 경우도 여기로 온다."""

    code = "VISIT_STATE_CONFLICT"


class VisitNotYetError(VisitError):
    """아직 할 수 없는 행동 — 미래 날의 시작·완료, 예약 시각 전의 노쇼."""

    code = "VISIT_NOT_YET"


class VisitDuplicateError(VisitError):
    """같은 반려동물(보호자만이면 같은 보호자)의 같은 시각에 살아 있는 예약이 이미 있다."""

    code = "VISIT_DUPLICATE"


class VisitCrossesMidnightError(VisitError):
    code = "VISIT_CROSSES_MIDNIGHT"


class VisitGroupMismatchError(VisitError):
    """한 번에 다루는 방문들이 같은 보호자의 방문이 아니다."""

    code = "VISIT_GROUP_MISMATCH"


class MenuNotFoundError(VisitError):
    """경로의 메뉴가 없거나 다른 매장의 것이다. 404."""

    code = "MENU_NOT_FOUND"


class MenuNotAvailableError(VisitError):
    """요청 본문의 메뉴가 이 매장의 보관되지 않은 메뉴가 아니다. 코드는 MENU_NOT_FOUND 로 같고 422 다."""

    code = "MENU_NOT_FOUND"


class MenuNameTakenError(VisitError):
    code = "MENU_NAME_TAKEN"


class VisitNoRecordYetError(VisitError):
    """예약됨·취소·노쇼 방문에는 기록을 쓸 수 없다 — 미용을 시작해야 한다. 409."""

    code = "VISIT_NO_RECORD_YET"


class RecordNotFoundError(VisitError):
    """그 방문에 기록이 없다. 404."""

    code = "RECORD_NOT_FOUND"


class RecordVersionConflictError(VisitError):
    """보낸 버전이 지금 기록의 버전과 다르다 — 그 사이 다른 기기나 업로드 대기열이 기록을 바꿨다. 409."""

    code = "RECORD_VERSION_CONFLICT"


class RecordWeightWithoutPetError(VisitError):
    """보호자만의 방문에 몸무게를 적었다. 422."""

    code = "RECORD_WEIGHT_WITHOUT_PET"


class RecordItemDuplicateError(VisitError):
    """같은 메뉴를 두 번 적었다. 422."""

    code = "RECORD_ITEM_DUPLICATE"


class RecordMediaLimitError(VisitError):
    """방문 하나의 사진 30장·영상 3편을 넘는다. 422."""

    code = "MEDIA_LIMIT_EXCEEDED"


class RecordSalesForbiddenError(VisitError):
    """돈 칸(총액·항목·결제 수단)을 적는데 sales:write 가 없다. 403."""

    code = "PERMISSION_DENIED"


class ReportNotFoundError(VisitError):
    """살아 있는 알림장 링크가 없다 — 끊을 링크가 없거나, 토큰이 틀렸거나, 그런 링크가 없다. 404."""

    code = "REPORT_NOT_FOUND"


class ReportClosedError(VisitError):
    """끊었거나 기간이 지난 링크, 또는 정지·폐업한 매장의 링크다. 410."""

    code = "REPORT_CLOSED"


class ReportEmptyError(VisitError):
    """보여 줄 사진·영상도 케어 메모도 없다. 링크를 새로 만들 때만 본다. 422."""

    code = "REPORT_EMPTY"


class VisitNotCompletedError(VisitError):
    """알림장은 완료한 방문에서만 보낸다. 409."""

    code = "VISIT_NOT_COMPLETED"


class VisitReportSentError(VisitError):
    """살아 있는 알림장 링크가 있는 방문은 되돌리거나 기록을 지울 수 없다 — 링크를 먼저 끊는다. 409."""

    code = "VISIT_REPORT_SENT"


class TooManyReportRequestsError(VisitError):
    """공개 알림장 조회가 너무 잦다. 코드는 초대 코드 시도 제한(tenancy)과 같다. 429."""

    code = "TOO_MANY_ATTEMPTS"


class VisitSeriesNotFoundError(VisitError):
    """반복 묶음이 없거나 다른 매장의 것(⑭)."""

    code = "VISIT_SERIES_NOT_FOUND"


class VisitSeriesConflictError(VisitError):
    """`이후 전부` 의 옮길 자리에 걸린 회차가 있다(⑭) — 아무것도 바꾸지 않았다. details 에는 방문·아이 ID, 매장
    시간대의 시각, 사유(taken·out_of_range)만 싣는다(이름·글은 싣지 않는다)."""

    code = "VISIT_SERIES_CONFLICT"

    def __init__(self, conflicts: Sequence[SeriesConflict], tz: str) -> None:
        super().__init__("이미 예약이 있거나 잡을 수 없는 회차가 있어요.")
        zone = ZoneInfo(tz)
        self.details = {"conflicts": [
            {"visit_id": c.visit_id, "pet_id": c.pet_id, "starts_at": c.starts_at.astimezone(zone).isoformat(),
             "reason": c.reason}
            for c in conflicts
        ]}
