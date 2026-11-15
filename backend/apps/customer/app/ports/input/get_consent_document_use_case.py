from __future__ import annotations

from abc import ABC, abstractmethod

from customer.app.dtos.consent_view_dto import ConsentDocumentView
from customer.app.dtos.get_consent_document_dto import GetConsentDocumentQuery


class GetConsentDocumentUseCase(ABC):
    @abstractmethod
    async def get_consent_document(self, query: GetConsentDocumentQuery) -> ConsentDocumentView: ...
