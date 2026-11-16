class GuardianError(Exception):
    """guardian 도메인 오류의 바탕. code 는 응답 본문의 code 로 나간다."""

    code = "GUARDIAN_ERROR"


class GuardianAlreadyLinkedError(GuardianError):
    """그 고객 카드가 이미 다른 계정에 이어져 있다. 409."""

    code = "GUARDIAN_ALREADY_LINKED"


class GuardianLinkNotFoundError(GuardianError):
    """없거나 남의 연결, 끝난 연결. 404 — 셋을 구분해 주지 않는다."""

    code = "GUARDIAN_LINK_NOT_FOUND"


class TooManyGuardianRequestsError(GuardianError):
    """잇기 시도가 잦다. 429."""

    code = "GUARDIAN_RATE_LIMITED"


class ReportLinkNotFoundError(GuardianError):
    """잇기: 토큰이 없거나 우리가 만든 것이 아니다. 404 — 공개 알림장과 같은 코드다."""

    code = "REPORT_NOT_FOUND"


class ReportLinkClosedError(GuardianError):
    """잇기: 닫힌 알림장(끊음·기간 지남·매장 정지·익명화·기록 없음). 410 — 공개 알림장과 같은 코드다."""

    code = "REPORT_CLOSED"


class GuardianFamilyFullError(GuardianError):
    """가족이 매장이 정한 수만큼 찼다(0 이면 초대가 없다). 409."""

    code = "GUARDIAN_FAMILY_FULL"


class GuardianInviteNotFoundError(GuardianError):
    """가족 초대가 없거나 쓰였거나 죽었거나 기간이 지났거나 기본 연결이 끝났다. 404 — 가르지 않는다."""

    code = "GUARDIAN_INVITE_NOT_FOUND"


class GuardianInputError(GuardianError):
    """형식은 맞지만 규칙에 어긋난 입력(가족 수의 범위). 422."""

    code = "VALIDATION_ERROR"


class GuardianAccountInactiveError(GuardianError):
    """탈퇴했거나 정지된 계정이다(유저 행을 잠그고 다시 봤다). 401 — 다시 로그인하라고 한다."""

    code = "UNAUTHENTICATED"
