"""auth 도메인 오류 → HTTP 상태 코드. 유스케이스는 HTTP 를 모른다."""
from auth.domain.errors import (
    AccountSuspendedError,
    IdentityAlreadyLinkedError,
    IdentityNotFoundError,
    InvalidRefreshTokenError,
    LastIdentityError,
    ProviderAlreadyLinkedError,
    ProviderVerificationError,
    RefreshTokenReuseError,
    UnsupportedProviderError,
    UserNotFoundError,
)

AUTH_ERROR_STATUS: dict[type[Exception], int] = {
    UnsupportedProviderError: 400,
    ProviderVerificationError: 401,
    InvalidRefreshTokenError: 401,
    RefreshTokenReuseError: 401,
    UserNotFoundError: 401,
    AccountSuspendedError: 403,
    IdentityAlreadyLinkedError: 409,
    IdentityNotFoundError: 404,
    ProviderAlreadyLinkedError: 409,
    LastIdentityError: 409,
}
