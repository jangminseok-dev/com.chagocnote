"""platform_admin 도메인 오류 → HTTP 상태 코드."""
from platform_admin.domain.errors import NotAnOperatorError

PLATFORM_ADMIN_ERROR_STATUS: dict[type[Exception], int] = {
    NotAnOperatorError: 403,
}
