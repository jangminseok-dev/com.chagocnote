from __future__ import annotations

from abc import ABC, abstractmethod

from customer.app.dtos.consent_view_dto import SignatureDetailView
from customer.app.dtos.get_consent_signature_dto import GetConsentSignatureQuery


class GetConsentSignatureUseCase(ABC):
    @abstractmethod
    async def get_consent_signature(self, query: GetConsentSignatureQuery) -> SignatureDetailView: ...
