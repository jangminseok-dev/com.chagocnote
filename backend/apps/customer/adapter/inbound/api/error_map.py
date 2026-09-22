"""customer 도메인 오류 → HTTP 상태 코드. 유스케이스는 HTTP 를 모른다."""
from customer.domain.errors import (
    CustomerInputError,
    CustomerNotFoundError,
    CustomerPhoneTakenError,
    LastPetError,
    PetHealthConflictError,
    PetHealthRequiredError,
    PetNotFoundError,
)

CUSTOMER_ERROR_STATUS: dict[type[Exception], int] = {
    CustomerNotFoundError: 404,
    PetNotFoundError: 404,
    CustomerPhoneTakenError: 409,
    LastPetError: 409,
    CustomerInputError: 422,
    PetHealthRequiredError: 422,
    PetHealthConflictError: 422,
}
