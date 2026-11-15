from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from customer.app.dtos.consent_view_dto import ConsentDocumentView


@dataclass(frozen=True)
class ReadPublicFormQuery:
    token: str | None      # 헤더로 받은 값 — 로그에 남기지 않는다
    client: str            # 접속 주소(횟수 제한용)


@dataclass(frozen=True)
class SubmitPublicConsentCommand:
    token: str | None
    client: str
    doc_digest: str
    signer_name: str
    signature_png: bytes


@dataclass(frozen=True)
class PublicFormView:
    """보호자가 보는 서류. document 가 있으면 열려 있고, 없으면 낸(또는 매장에서 이미 받은) 것이다."""

    shop_name: str
    document: ConsentDocumentView | None
    submitted_on: date | None
