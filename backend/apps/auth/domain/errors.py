class AuthError(Exception):
    """auth 도메인 오류의 바탕. code 는 응답 본문의 code 로 나간다."""

    code = "AUTH_ERROR"


class UnsupportedProviderError(AuthError):
    code = "PROVIDER_NOT_SUPPORTED"


class ProviderVerificationError(AuthError):
    code = "PROVIDER_VERIFICATION_FAILED"


class AccountSuspendedError(AuthError):
    code = "ACCOUNT_SUSPENDED"


class InvalidRefreshTokenError(AuthError):
    code = "UNAUTHENTICATED"


class RefreshTokenReuseError(AuthError):
    code = "UNAUTHENTICATED"


class UserNotFoundError(AuthError):
    code = "UNAUTHENTICATED"


class IdentityAlreadyLinkedError(AuthError):
    code = "IDENTITY_ALREADY_LINKED"
