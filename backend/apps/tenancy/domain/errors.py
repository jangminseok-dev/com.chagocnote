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


class AccountUnavailableError(TenancyError):
    """요청 시작 때는 인증을 통과했지만, 유저 행을 잠근 뒤에 보니 탈퇴했거나 정지된 유저다.

    정지도 여기로 들어와 401 이 된다. 인증 가드(`core/security.py`)는 같은 상태를 403 ACCOUNT_SUSPENDED 로
    돌려주므로, 다시 요청하면 그쪽으로 수렴한다. 가드 조회와 잠금 사이의 좁은 틈에서만 이 오류가 나간다.
    """

    code = "UNAUTHENTICATED"
