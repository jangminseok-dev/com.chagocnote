from __future__ import annotations

from abc import ABC, abstractmethod

from customer.app.dtos.get_consent_signature_image_dto import GetConsentSignatureImageQuery


class GetConsentSignatureImageUseCase(ABC):
    @abstractmethod
    async def get_consent_signature_image(self, query: GetConsentSignatureImageQuery) -> bytes: ...
