class TenancyError(Exception):
    """tenancy 도메인 오류의 바탕. code 는 응답 본문의 code 로 나간다."""

    code = "TENANCY_ERROR"


class NotAMemberError(TenancyError):
    code = "NOT_A_MEMBER"


class ShopClosedError(TenancyError):
    code = "SHOP_CLOSED"


class ShopSuspendedError(TenancyError):
    code = "SHOP_SUSPENDED"


class LastOwnerError(TenancyError):
    code = "LAST_OWNER"


class MemberNotFoundError(TenancyError):
    code = "MEMBER_NOT_FOUND"


class AlreadyMemberError(TenancyError):
    code = "ALREADY_A_MEMBER"


class InviteInvalidError(TenancyError):
    code = "INVITE_INVALID"


class InviteExpiredError(TenancyError):
    code = "INVITE_EXPIRED"


class InviteExhaustedError(TenancyError):
    code = "INVITE_EXHAUSTED"


class TooManyAttemptsError(TenancyError):
    code = "TOO_MANY_ATTEMPTS"


class OwnershipTransferRequiredError(TenancyError):
    code = "OWNERSHIP_TRANSFER_REQUIRED"


class ShopCloseConfirmRequiredError(TenancyError):
    code = "SHOP_CLOSE_CONFIRM_REQUIRED"
