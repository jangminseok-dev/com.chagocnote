"""visit 도메인 오류 → HTTP 상태 코드. 유스케이스는 HTTP 를 모른다."""
from visit.domain.errors import (
    MenuNameTakenError,
    MenuNotAvailableError,
    MenuNotFoundError,
    VisitCrossesMidnightError,
    VisitDuplicateError,
    VisitGroupMismatchError,
    VisitInputError,
    VisitNotFoundError,
    VisitNotYetError,
    VisitStateConflictError,
)

VISIT_ERROR_STATUS: dict[type[Exception], int] = {
    VisitNotFoundError: 404,
    MenuNotFoundError: 404,
    VisitStateConflictError: 409,
    VisitNotYetError: 409,
    VisitDuplicateError: 409,
    MenuNameTakenError: 409,
    VisitInputError: 422,
    VisitCrossesMidnightError: 422,
    VisitGroupMismatchError: 422,
    MenuNotAvailableError: 422,
}
