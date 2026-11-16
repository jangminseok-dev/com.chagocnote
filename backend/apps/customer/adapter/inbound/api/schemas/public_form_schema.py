"""로그인 없는 서류 경로의 요청·응답(⑪-A). 매장용 스키마와 따로 쓰고 칸을 하나하나 적는다.

싣지 않는 것: 고객·반려동물·매장·요청·서명의 ID, 전화번호, 지병 메모, 반려동물 메모, 주의·노쇼, 다른 가족의 아이.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from decimal import Decimal
from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field, StrictBool, StringConstraints, field_validator

from customer.adapter.inbound.api.schemas.consent_schema import SignaturePng, decode_png
from customer.adapter.inbound.api.schemas.text_validators import reject_control_chars
from customer.app.dtos.public_form_dto import PublicFormView
from customer.domain.services.intake_rules import IntakeEntry
from customer.domain.value_objects.condition_entry import ConditionEntry

# 알림장의 공개 응답과 같은 헤더다 — 어디에도 저장하지 않고 검색에 걸리지 않는다.
PUBLIC_FORM_HEADERS = {"Cache-Control": "private, no-store", "X-Robots-Tag": "noindex, nofollow"}


class PublicFormShopSchema(BaseModel):
    name: str


class PublicFormPetSchema(BaseModel):
    name: str
    conditions: list[str]     # 지병의 이름뿐 — 메모는 싣지 않는다
    parts: list[str]


class PublicFormTextSchema(BaseModel):
    body: str


class PublicOpenFormSchema(BaseModel):
    kind: str
    state: str
    shop: PublicFormShopSchema
    previous_consent_on: date | None
    pets: list[PublicFormPetSchema]
    texts: dict[str, PublicFormTextSchema]
    doc_digest: str


class PublicSubmittedFormSchema(BaseModel):
    kind: str
    state: str
    shop: PublicFormShopSchema
    submitted_on: date | None


class PublicIntakeQuestionSchema(BaseModel):
    question_id: int      # 답이 가리킨다 — 공개 응답에 싣는 유일한 ID
    label: str
    required: bool


class PublicConditionTypeSchema(BaseModel):
    code: str
    label: str


class PublicOpenIntakeSchema(BaseModel):
    """열린 문진표의 구성. 지금 값(품종·몸무게·지병)·전화번호·ID 는 싣지 않는다."""

    kind: str
    state: str
    shop: PublicFormShopSchema
    mode: str                     # new | add_pet | update
    pet_name: str | None          # 다시 받기일 때만
    fields: list[str]             # 켜진 칸
    questions: list[PublicIntakeQuestionSchema]
    condition_types: list[PublicConditionTypeSchema]
    answered: int                 # 이 링크로 이미 낸 답의 수
    guardian_needed: bool         # 보호자 이름·번호를 적어야 하나


def public_form_body(view: PublicFormView) -> dict[str, Any]:
    shop = PublicFormShopSchema(name=view.shop_name)
    if view.intake is not None:
        intake = view.intake
        return PublicOpenIntakeSchema(
            kind="intake", state="open", shop=shop, mode=intake.mode, pet_name=intake.pet_name,
            fields=list(intake.fields),
            questions=[PublicIntakeQuestionSchema(question_id=q.id, label=q.label, required=q.required)
                       for q in intake.questions],
            condition_types=[PublicConditionTypeSchema(code=code, label=label)
                             for code, label in intake.condition_types],
            answered=intake.answered, guardian_needed=intake.guardian_needed,
        ).model_dump(mode="json")
    if view.document is None:
        return PublicSubmittedFormSchema(
            kind=view.kind, state="submitted", shop=shop, submitted_on=view.submitted_on,
        ).model_dump(mode="json")
    doc = view.document
    return PublicOpenFormSchema(
        kind="consent", state="open", shop=shop, previous_consent_on=doc.previous_consent_on,
        pets=[PublicFormPetSchema(name=p.name, conditions=list(p.conditions), parts=list(p.parts)) for p in doc.pets],
        texts={part: PublicFormTextSchema(body=body) for part, body in doc.texts.items()},
        doc_digest=doc.doc_digest,
    ).model_dump(mode="json")


class SubmitPublicConsentRequestSchema(BaseModel):
    doc_digest: str = Field(min_length=1, max_length=128)
    signer_name: str = Field(max_length=200)
    signature_png: SignaturePng

    @field_validator("signature_png")
    @classmethod
    def _is_base64(cls, value: str) -> str:
        decode_png(value)
        return value

    def png(self) -> bytes:
        return decode_png(self.signature_png)


# --- 문진표 제출(⑪-C) ------------------------------------------------------------------------------------------------

_NoControl = AfterValidator(reject_control_chars)
_Text50 = Annotated[str, StringConstraints(strip_whitespace=True, max_length=50), _NoControl] | None
_Text30 = Annotated[str, StringConstraints(strip_whitespace=True, max_length=30), _NoControl] | None
_Text100 = Annotated[str, StringConstraints(strip_whitespace=True, max_length=100), _NoControl] | None
_Text200 = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200), _NoControl] | None
_MAX_BIGINT = 9_223_372_036_854_775_807


class PublicIntakeGuardianSchema(BaseModel):
    name: _Text50 = None
    phone: Annotated[str, StringConstraints(strip_whitespace=True, max_length=20), _NoControl] | None = None


class PublicIntakeConditionSchema(BaseModel):
    type_code: Annotated[str, StringConstraints(min_length=1, max_length=30), _NoControl]
    custom_label: _Text30 = None
    note: _Text100 = None


class PublicIntakePetSchema(BaseModel):
    """칸의 필수 여부는 도메인이 본다(켜진 칸·보내는 곳에 따라 다르다) — 여기서는 모양과 길이만."""

    name: _Text50 = None
    species: Annotated[str, StringConstraints(max_length=10)] | None = None
    breed: _Text50 = None
    sex: Annotated[str, StringConstraints(max_length=10)] | None = None
    neutered: StrictBool | None = None
    birth_date: date | None = None
    birth_year: Annotated[int, Field(ge=0, le=9999)] | None = None
    birth_unknown: StrictBool = False
    weight_kg: Annotated[Decimal, Field(max_digits=4, decimal_places=1)] | None = None
    weight_unknown: StrictBool = False
    no_known_conditions: StrictBool | None = None
    conditions: Annotated[list[PublicIntakeConditionSchema], Field(max_length=20)] = []
    dislikes: _Text200 = None
    style: _Text200 = None


class PublicIntakeExtraSchema(BaseModel):
    question_id: Annotated[int, Field(ge=1, le=_MAX_BIGINT)]
    body: Annotated[str, StringConstraints(strip_whitespace=True, max_length=200), _NoControl]


class SubmitPublicIntakeRequestSchema(BaseModel):
    guardian: PublicIntakeGuardianSchema | None = None
    pet: PublicIntakePetSchema
    extras: Annotated[list[PublicIntakeExtraSchema], Field(max_length=20)] = []
    privacy_agreed: StrictBool
    done: StrictBool = False

    def to_entry(self) -> IntakeEntry:
        guardian, pet = self.guardian or PublicIntakeGuardianSchema(), self.pet
        return IntakeEntry(
            guardian_name=guardian.name or None, guardian_phone=guardian.phone or None, pet_name=pet.name or None,
            species=pet.species or None, breed=pet.breed or None, sex=pet.sex or None, neutered=pet.neutered,
            birth_date=pet.birth_date, birth_year=pet.birth_year, birth_unknown=pet.birth_unknown,
            weight_kg=pet.weight_kg, weight_unknown=pet.weight_unknown,
            no_known_conditions=pet.no_known_conditions,
            conditions=tuple(
                ConditionEntry(type_code=c.type_code, custom_label=c.custom_label or None, note=c.note or None)
                for c in pet.conditions),
            dislikes=pet.dislikes or None, style=pet.style or None,
            extras=tuple((extra.question_id, extra.body) for extra in self.extras),
            privacy_agreed=self.privacy_agreed,
        )
