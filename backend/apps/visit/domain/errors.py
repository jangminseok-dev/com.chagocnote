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
