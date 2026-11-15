"""동의서 경로의 요청·응답(⑪-A, 매장용). 공개 경로의 스키마는 따로 쓴다."""
from __future__ import annotations

import base64
import binascii
from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, Field, field_validator

from customer.app.dtos.consent_view_dto import (
    ConsentDocumentView,
    FormLinkView,
    SentFormView,
    SignatureBriefView,
    SignatureDetailView,
)

_MAX_BIGINT = 9_223_372_036_854_775_807
PetIds = Annotated[list[Annotated[int, Field(ge=1, le=_MAX_BIGINT)]], Field(min_length=1, max_length=10)]
# 65,536바이트의 base64 는 87,384글자다.
SignaturePng = Annotated[str, Field(min_length=1, max_length=87_400)]


def decode_png(value: str) -> bytes:
    """base64 를 바이트로. 틀리면 ValueError — 422 가 된다. 오류 글에 값을 싣지 않는다."""
    try:
        return base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError):
        raise ValueError("서명 그림이 올바르지 않습니다.") from None


class IssueConsentFormRequestSchema(BaseModel):
    pet_ids: PetIds


class FormLinkSchema(BaseModel):
    form_id: int
    url: str
    expires_on: date
    sent_on: date

    @classmethod
    def of(cls, view: FormLinkView) -> "FormLinkSchema":
        return cls(form_id=view.form_id, url=view.url, expires_on=view.expires_on, sent_on=view.sent_on)


class FormCustomerSchema(BaseModel):
    customer_id: int
    name: str


class FormPetSchema(BaseModel):
    pet_id: int
    name: str


class SentFormSchema(BaseModel):
    form_id: int
    kind: str
    customer: FormCustomerSchema
    pets: list[FormPetSchema]
    sent_on: date
    expires_on: date
    url: str


class SentFormsSchema(BaseModel):
    items: list[SentFormSchema]

    @classmethod
    def of(cls, views: list[SentFormView]) -> "SentFormsSchema":
        return cls(items=[
            SentFormSchema(
                form_id=v.form_id, kind=v.kind,
                customer=FormCustomerSchema(customer_id=v.customer_id, name=v.customer_name),
                pets=[FormPetSchema(pet_id=p.pet_id, name=p.name) for p in v.pets],
                sent_on=v.sent_on, expires_on=v.expires_on, url=v.url,
            )
            for v in views
        ])


class DocumentPetSchema(BaseModel):
    pet_id: int
    name: str
    conditions: list[str]
    parts: list[str]


class DocumentTextSchema(BaseModel):
    body: str


class ConsentDocumentSchema(BaseModel):
    pets: list[DocumentPetSchema]
    texts: dict[str, DocumentTextSchema]
    previous_consent_on: date | None
    doc_digest: str

    @classmethod
    def of(cls, view: ConsentDocumentView) -> "ConsentDocumentSchema":
        return cls(
            pets=[DocumentPetSchema(pet_id=p.pet_id, name=p.name, conditions=list(p.conditions), parts=list(p.parts))
                  for p in view.pets],
            texts={part: DocumentTextSchema(body=body) for part, body in view.texts.items()},
            previous_consent_on=view.previous_consent_on, doc_digest=view.doc_digest,
        )


class SignConsentRequestSchema(BaseModel):
    pet_ids: PetIds
    doc_digest: str = Field(min_length=1, max_length=128)
    signer_name: str = Field(max_length=200)     # 1~50자는 유스케이스가 앞뒤 공백을 뗀 뒤에 본다
    signature_png: SignaturePng

    @field_validator("signature_png")
    @classmethod
    def _is_base64(cls, value: str) -> str:
        decode_png(value)
        return value

    def png(self) -> bytes:
        return decode_png(self.signature_png)


class SignedSchema(BaseModel):
    signature_id: int


class SignatureBriefSchema(BaseModel):
    signature_id: int
    signed_at: datetime
    channel: str
    signer_name: str
    parts: list[str]


class SignatureBriefsSchema(BaseModel):
    items: list[SignatureBriefSchema]

    @classmethod
    def of(cls, views: list[SignatureBriefView]) -> "SignatureBriefsSchema":
        return cls(items=[
            SignatureBriefSchema(signature_id=v.signature_id, signed_at=v.signed_at, channel=v.channel,
                                 signer_name=v.signer_name, parts=list(v.parts))
            for v in views
        ])


class SignedPartSchema(BaseModel):
    part: str
    body: str


class SignaturePetSchema(BaseModel):
    pet_id: int | None
    shown_name: str
    conditions: list[str]
    parts: list[SignedPartSchema]


class SignatureDetailSchema(BaseModel):
    signature_id: int
    signed_at: datetime
    channel: str
    signer_name: str
    by_member_id: int
    pets: list[SignaturePetSchema]

    @classmethod
    def of(cls, view: SignatureDetailView) -> "SignatureDetailSchema":
        return cls(
            signature_id=view.signature_id, signed_at=view.signed_at, channel=view.channel,
            signer_name=view.signer_name, by_member_id=view.by_member_id,
            pets=[
                SignaturePetSchema(
                    pet_id=p.pet_id, shown_name=p.shown_name, conditions=list(p.conditions),
                    parts=[SignedPartSchema(part=x.part, body=x.body) for x in p.parts],
                )
                for p in view.pets
            ],
        )
