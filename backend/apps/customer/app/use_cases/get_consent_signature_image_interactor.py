from __future__ import annotations

from customer.app.dtos.get_consent_signature_image_dto import GetConsentSignatureImageQuery
from customer.app.ports.input.get_consent_signature_image_use_case import GetConsentSignatureImageUseCase
from customer.app.ports.output.consent_signature_repository import ConsentSignatureRepository


class GetConsentSignatureImageInteractor(GetConsentSignatureImageUseCase):
    def __init__(self, signatures: ConsentSignatureRepository) -> None:
        self._signatures = signatures

    async def get_consent_signature_image(self, query: GetConsentSignatureImageQuery) -> bytes:
        return await self._signatures.image(query.ctx, query.signature_id)
