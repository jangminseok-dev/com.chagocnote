"""guardian 도메인 오류 → HTTP 상태 코드. 유스케이스는 HTTP 를 모른다."""
from guardian.domain.errors import (
    GuardianAccountInactiveError,
    GuardianAlreadyLinkedError,
    GuardianLinkNotFoundError,
    ReportLinkClosedError,
    ReportLinkNotFoundError,
    TooManyGuardianRequestsError,
)

GUARDIAN_ERROR_STATUS: dict[type[Exception], int] = {
    GuardianAlreadyLinkedError: 409,
    GuardianLinkNotFoundError: 404,
    TooManyGuardianRequestsError: 429,
    ReportLinkNotFoundError: 404,
    ReportLinkClosedError: 410,
    GuardianAccountInactiveError: 401,
}
