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


class ProviderRevokeError(AuthError):
    """제공자 쪽 연결을 끊지 못했다. HTTP 응답으로 나가지 않는다 — 부르는 쪽이 로그로 남긴다."""

    code = "PROVIDER_REVOKE_FAILED"


class ProviderAlreadyLinkedError(AuthError):
    code = "PROVIDER_ALREADY_LINKED"


class LastIdentityError(AuthError):
    code = "LAST_IDENTITY"


class IdentityNotFoundError(AuthError):
    code = "IDENTITY_NOT_FOUND"
