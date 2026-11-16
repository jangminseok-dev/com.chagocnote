class CustomerError(Exception):
    """customer 도메인 오류의 바탕. code 는 응답 본문의 code 로 나간다."""

    code = "CUSTOMER_ERROR"


class CustomerInputError(CustomerError):
    """형식은 맞지만 규칙에 어긋난 입력(전화번호 형식, 나이, 질병 항목, 커서). 스키마 검증과 같은 422 다."""

    code = "VALIDATION_ERROR"


class CustomerNotFoundError(CustomerError):
    code = "CUSTOMER_NOT_FOUND"


class PetNotFoundError(CustomerError):
    code = "PET_NOT_FOUND"


class CustomerPhoneTakenError(CustomerError):
    code = "CUSTOMER_PHONE_TAKEN"


class LastPetError(CustomerError):
    code = "LAST_PET"


class PetHealthRequiredError(CustomerError):
    code = "PET_HEALTH_REQUIRED"


class PetHealthConflictError(CustomerError):
    code = "PET_HEALTH_CONFLICT"


class PetHasVisitsError(CustomerError):
    """방문 기록이 있는 반려동물은 지우지 않는다 — 무지개다리를 쓴다."""

    code = "PET_HAS_VISITS"


class PetHasUpcomingVisitsError(CustomerError):
    """앞으로의 예약이 남은 아이는 무지개다리로 표시하지 않는다 — 예약을 먼저 취소한다."""

    code = "PET_HAS_UPCOMING_VISITS"


class CustomerHasUpcomingVisitsError(CustomerError):
    """앞으로의 예약이 남은 고객은 익명화하지 않는다 — 예약을 먼저 취소한다."""

    code = "CUSTOMER_HAS_UPCOMING_VISITS"


class PetPassedAwayError(CustomerError):
    """무지개다리 아이에게 예약을 잡으려 했다."""

    code = "PET_PASSED_AWAY"


class IntakeAnswerNotFoundError(CustomerError):
    """받은 문진표가 없다 — 이미 등록했거나 지웠거나 보관 기간이 지났다."""

    code = "INTAKE_ANSWER_NOT_FOUND"


class FormNotFoundError(CustomerError):
    """서류 요청이 없다(또는 다른 매장의 것, 서명이 틀린 토큰). 오류에 요청·고객의 값을 싣지 않는다."""

    code = "FORM_NOT_FOUND"


class FormClosedError(CustomerError):
    """끊었거나 기간이 지났거나 이미 낸 서류. 닫힌 이유는 가르지 않는다."""

    code = "FORM_CLOSED"


class SignatureNotFoundError(CustomerError):
    code = "SIGNATURE_NOT_FOUND"


class ConsentDocumentChangedError(CustomerError):
    """보호자가 읽은 뒤 동의서의 내용(아이 이름·지병·토막·글의 판)이 바뀌었다 — 다시 읽게 한다."""

    code = "CONSENT_DOCUMENT_CHANGED"


class ConsentRequiredError(CustomerError):
    """문진표의 답으로 보아 동의서 구역이 나타나야 하는데 서명이 없거나 필요한 토막을 읽지 않았다(⑪-C1b)."""

    code = "CONSENT_REQUIRED"


class ConsentUpToDateError(CustomerError):
    """다시 받을 토막이 하나도 없다."""

    code = "CONSENT_UP_TO_DATE"


class TooManyFormRequestsError(CustomerError):
    """공개 서류 경로의 횟수 제한에 걸렸다. 알림장의 것과 같은 code 다 — 웹이 같은 화면으로 받는다."""

    code = "TOO_MANY_ATTEMPTS"

