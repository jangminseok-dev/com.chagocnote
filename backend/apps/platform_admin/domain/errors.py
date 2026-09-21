class PlatformAdminError(Exception):
    """platform_admin 도메인 오류의 바탕. code 는 응답 본문의 code 로 나간다."""

    code = "PLATFORM_ADMIN_ERROR"


class NotAnOperatorError(PlatformAdminError):
    code = "PERMISSION_DENIED"
