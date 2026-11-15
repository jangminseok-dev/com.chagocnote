"""로그인 없는 서류 경로의 요청·응답(⑪-A). 매장용 스키마와 따로 쓰고 칸을 하나하나 적는다.

싣지 않는 것: 고객·반려동물·매장·요청·서명의 ID, 전화번호, 지병 메모, 반려동물 메모, 주의·노쇼, 다른 가족의 아이.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field, field_validator

from customer.adapter.inbound.api.schemas.consent_schema import SignaturePng, decode_png
from customer.app.dtos.public_form_dto import PublicFormView

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


def public_form_body(view: PublicFormView) -> dict[str, Any]:
    shop = PublicFormShopSchema(name=view.shop_name)
    if view.document is None:
        return PublicSubmittedFormSchema(
            kind="consent", state="submitted", shop=shop, submitted_on=view.submitted_on,
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
