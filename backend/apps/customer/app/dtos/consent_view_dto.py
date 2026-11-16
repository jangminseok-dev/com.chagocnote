"""동의서 화면들이 함께 쓰는 보기(⑪-A)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class FormLinkView:
    form_id: int
    url: str               # 보호자가 여는 주소 — 로그에 남기지 않는다
    expires_on: date       # 매장 시간대의 날
    sent_on: date
    created: bool          # 이번에 새로 만들었나(아니면 살아 있던 것)


@dataclass(frozen=True)
class FormPetView:
    pet_id: int
    name: str


@dataclass(frozen=True)
class SentFormView:
    form_id: int
    kind: str
    customer_id: int
    customer_name: str
    pets: tuple[FormPetView, ...]
    sent_on: date
    expires_on: date
    url: str


@dataclass(frozen=True)
class DocumentPetView:
    pet_id: int
    name: str
    conditions: tuple[str, ...]
    parts: tuple[str, ...]


@dataclass(frozen=True)
class ConsentDocumentView:
    pets: tuple[DocumentPetView, ...]
    texts: dict[str, str]              # 토막 → 글
    previous_consent_on: date | None
    doc_digest: str


@dataclass(frozen=True)
class SignatureBriefView:
    signature_id: int
    signed_at: datetime
    channel: str
    signer_name: str
    parts: tuple[str, ...]


@dataclass(frozen=True)
class SignedPartView:
    part: str
    body: str               # 그 판의 글자


@dataclass(frozen=True)
class SignaturePetView:
    pet_id: int | None
    shown_name: str
    conditions: tuple[str, ...]
    parts: tuple[SignedPartView, ...]


@dataclass(frozen=True)
class SignatureDetailView:
    signature_id: int
    signed_at: datetime
    channel: str
    signer_name: str
    by_member_id: int
    pets: tuple[SignaturePetView, ...]
