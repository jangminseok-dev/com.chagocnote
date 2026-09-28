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
