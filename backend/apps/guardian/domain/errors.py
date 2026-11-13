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
