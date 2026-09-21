"""tenancy 도메인 오류 → HTTP 상태 코드. 유스케이스는 HTTP 를 모른다."""
from tenancy.domain.errors import (
    AlreadyMemberError,
    InviteExhaustedError,
    InviteExpiredError,
    InviteInvalidError,
    LastOwnerError,
    MemberNotFoundError,
    NotAMemberError,
    ShopClosedError,
    ShopSuspendedError,
    TooManyAttemptsError,
)

TENANCY_ERROR_STATUS: dict[type[Exception], int] = {
    InviteInvalidError: 400,
    InviteExpiredError: 400,
    InviteExhaustedError: 400,
    NotAMemberError: 403,
    ShopClosedError: 403,
    ShopSuspendedError: 403,
    MemberNotFoundError: 404,
    LastOwnerError: 409,
    AlreadyMemberError: 409,
    TooManyAttemptsError: 429,
}
