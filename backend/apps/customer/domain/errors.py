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
