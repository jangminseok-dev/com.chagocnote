from __future__ import annotations

from datetime import date
from decimal import Decimal
from functools import partial
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, Field, StrictBool, StringConstraints

from customer.adapter.inbound.api.schemas.text_validators import reject_control_chars
from customer.app.dtos.customer_input_dto import CustomerInput, PetInput
from customer.domain.value_objects.condition_entry import ConditionEntry

_NoControlChars = AfterValidator(reject_control_chars)
# 메모만 개행을 허용한다.
_NoControlCharsAllowNewline = AfterValidator(partial(reject_control_chars, allow_newline=True))

Required50 = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50), _NoControlChars
]

# 앞뒤 공백을 없앤 선택 문자열. 빈 문자열은 to_input 이 None 으로 바꾼다.
Optional20 = Annotated[
    str, StringConstraints(strip_whitespace=True, max_length=20), _NoControlChars
] | None
Optional30 = Annotated[
    str, StringConstraints(strip_whitespace=True, max_length=30), _NoControlChars
] | None
Optional100 = Annotated[
    str, StringConstraints(strip_whitespace=True, max_length=100), _NoControlChars
] | None
Optional500 = Annotated[
    str, StringConstraints(strip_whitespace=True, max_length=500), _NoControlCharsAllowNewline
] | None


class CustomerFieldsSchema(BaseModel):
    """보호자 폼. 전화번호는 하이픈을 넣어 보내도 되고, 서버가 숫자만 남겨 검증한다."""

    name: Required50
    phone: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20), _NoControlChars
    ]
    phone_alt: Optional20 = None
    marketing_consent: StrictBool
    memo: Optional500 = None

    def to_input(self) -> CustomerInput:
        return CustomerInput(
            name=self.name, phone=self.phone, phone_alt=self.phone_alt or None,
            marketing_consent=self.marketing_consent, memo=self.memo or None,
        )


class ConditionSchema(BaseModel):
    type_code: Annotated[str, StringConstraints(min_length=1, max_length=30), _NoControlChars]
    custom_label: Optional30 = None
    note: Optional100 = None


class PetFieldsSchema(BaseModel):
    """반려동물 폼. 생일·태어난 해는 하나만(둘 다 없으면 모름), 질병은 목록 전체를 보낸다."""

    name: Required50
    species: Literal["dog", "cat"]
    breed: Required50
    sex: Literal["female", "male"]
    neutered: StrictBool
    birth_date: date | None = None
    birth_year: int | None = None
    weight_kg: Annotated[Decimal, Field(gt=0, max_digits=4, decimal_places=1)]
    no_known_conditions: StrictBool
    conditions: Annotated[list[ConditionSchema], Field(max_length=20)] = []
    memo: Optional500 = None

    def to_input(self) -> PetInput:
        return PetInput(
            name=self.name, species=self.species, breed=self.breed, sex=self.sex,
            neutered=self.neutered, birth_date=self.birth_date, birth_year=self.birth_year,
            weight_kg=self.weight_kg, no_known_conditions=self.no_known_conditions,
            memo=self.memo or None,
            conditions=tuple(
                ConditionEntry(type_code=c.type_code, custom_label=c.custom_label or None,
                               note=c.note or None)
                for c in self.conditions
            ),
        )


class RegisterCustomerRequestSchema(BaseModel):
    customer: CustomerFieldsSchema
    pet: PetFieldsSchema
