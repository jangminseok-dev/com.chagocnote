from __future__ import annotations

from collections.abc import Callable
from datetime import date

from customer.app.dtos.consent_view_dto import ConsentDocumentView, DocumentPetView
from customer.app.dtos.get_consent_document_dto import GetConsentDocumentQuery
from customer.app.ports.input.get_consent_document_use_case import GetConsentDocumentUseCase
from customer.app.ports.output.consent_signature_repository import ConsentSignatureRepository
from customer.app.ports.output.pet_repository import PetRepository
from customer.app.services.consent_reader import ConsentDocument, read_document
from customer.app.services.consent_source import ConsentSource
from customer.domain.errors import ConsentUpToDateError
from customer.domain.services.consent_document import base_date


def document_view(doc: ConsentDocument) -> ConsentDocumentView:
    return ConsentDocumentView(
        pets=tuple(DocumentPetView(p.pet_id, p.name, p.condition_labels, p.parts) for p in doc.pets),
        texts={part: text.body for part, text in doc.texts.items()},
        previous_consent_on=doc.previous_consent_on, doc_digest=doc.digest,
    )


class GetConsentDocumentInteractor(GetConsentDocumentUseCase):
    """매장에서 바로 서명받을 동의서(⑪ 설계 3.3). 링크가 없으니 서류 요청 행도 없다."""

    def __init__(
        self, pets: PetRepository, signatures: ConsentSignatureRepository, today: Callable[[], date],
        source: ConsentSource,
    ) -> None:
        self._pets = pets
        self._signatures = signatures
        self._today = today
        self._source = source

    async def get_consent_document(self, query: GetConsentDocumentQuery) -> ConsentDocumentView:
        policy = await self._source.policy(query.ctx)
        doc = await read_document(
            query.ctx, query.pet_ids, base_date(self._today(), query.for_date, policy), policy,
            pets=self._pets, signatures=self._signatures, texts=await self._source.texts(query.ctx))
        if not doc.pets:
            raise ConsentUpToDateError("이미 받은 동의입니다.")
        return document_view(doc)
