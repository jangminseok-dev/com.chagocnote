"""받은 문진표의 응답(⑪-C, 매장용). 이름·번호·적은 글이 들어 있다 — 로그에 남기지 않는다."""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from customer.app.dtos.intake_answer_view_dto import IntakeAnswerView
from customer.domain.services.phone_number import format_phone


class MatchedCustomerSchema(BaseModel):
    customer_id: int
    name: str


class IntakeAnswerItemSchema(BaseModel):
    answer_id: int
    mode: str                                    # new | add_pet | update
    pet_name: str | None
    guardian_name: str | None
    submitted_on: date
    matched_customer: MatchedCustomerSchema | None    # 미리 이어 둔 등록된 고객
    pet_id: int | None                           # 다시 받기일 때 — 그 아이

    @classmethod
    def fields_of(cls, view: IntakeAnswerView) -> dict:
        answer = view.answer
        matched = None
        if answer.matched_customer_id is not None and view.matched_customer_name is not None:
            matched = MatchedCustomerSchema(customer_id=answer.matched_customer_id, name=view.matched_customer_name)
        return {
            "answer_id": answer.id, "mode": answer.mode, "pet_name": view.pet_name,
            "guardian_name": answer.guardian_name, "submitted_on": view.submitted_on,
            "matched_customer": matched, "pet_id": answer.pet_id,
        }

    @classmethod
    def of(cls, view: IntakeAnswerView) -> "IntakeAnswerItemSchema":
        return cls(**cls.fields_of(view))


class IntakeAnswersSchema(BaseModel):
    items: list[IntakeAnswerItemSchema]

    @classmethod
    def of(cls, views: list[IntakeAnswerView]) -> "IntakeAnswersSchema":
        return cls(items=[IntakeAnswerItemSchema.of(view) for view in views])


class IntakeConditionSchema(BaseModel):
    type_code: str
    label: str
    custom_label: str | None
    note: str | None


class IntakeExtraSchema(BaseModel):
    label: str
    body: str


class IntakeConsentSchema(BaseModel):
    """끝의 동의서에서 맡아 둔 서명의 요약 — 그림과 적은 이름은 싣지 않는다."""

    signed_on: date           # 매장 시간대의 날
    parts: list[str]          # 보호자가 읽은 토막


class IntakeAnswerSchema(IntakeAnswerItemSchema):
    """한 장 — 답 전부. 끈 칸·모르겠어요는 null 이다(지어내지 않는다)."""

    guardian_phone: str | None
    species: str | None
    breed: str | None
    sex: str | None
    neutered: bool | None
    birth_date: date | None
    birth_year: int | None
    birth_unknown: bool
    weight_kg: float | None
    no_known_conditions: bool | None
    conditions: list[IntakeConditionSchema]
    dislikes: str | None
    style: str | None
    extras: list[IntakeExtraSchema]
    missing: list[str]        # 등록에 꼭 있어야 하는데 빈 칸 — 등록할 때 사장에게 묻는다
    memo_draft: str           # 반려동물 메모의 초안(싫어하는 것·스타일·질문의 답)
    memo_over: int            # 메모 칸(500자)을 넘친 글자 수 — 자르지 않는다
    consent: IntakeConsentSchema | None   # 끝의 동의서에서 맡아 둔 서명(⑪-C1b) — 등록하면 그 아이의 동의가 된다

    @classmethod
    def of(cls, view: IntakeAnswerView) -> "IntakeAnswerSchema":
        a = view.answer
        return cls(
            **cls.fields_of(view),
            guardian_phone=None if a.guardian_phone is None else format_phone(a.guardian_phone),
            species=a.species, breed=a.breed, sex=a.sex, neutered=a.neutered, birth_date=a.birth_date,
            birth_year=a.birth_year, birth_unknown=a.birth_unknown,
            weight_kg=None if a.weight_kg is None else float(a.weight_kg),
            no_known_conditions=a.no_known_conditions,
            conditions=[
                IntakeConditionSchema(
                    type_code=c.type_code, label=view.condition_labels.get(c.type_code, c.type_code),
                    custom_label=c.custom_label, note=c.note)
                for c in a.conditions
            ],
            dislikes=a.dislikes, style=a.style,
            extras=[IntakeExtraSchema(label=label, body=body) for label, body in a.extras],
            missing=list(view.missing), memo_draft=view.memo_draft, memo_over=view.memo_over,
            consent=None if view.consent is None else IntakeConsentSchema(
                signed_on=view.consent.signed_on,
                parts=list(view.consent.parts)),
        )
