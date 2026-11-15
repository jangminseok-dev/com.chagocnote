from __future__ import annotations

from customer.app.dtos.consent_view_dto import SignatureBriefView
from customer.app.dtos.list_pet_consent_signatures_dto import ListPetConsentSignaturesQuery
from customer.app.ports.input.list_pet_consent_signatures_use_case import ListPetConsentSignaturesUseCase
from customer.app.ports.output.consent_signature_repository import ConsentSignatureRepository
from customer.app.ports.output.pet_repository import PetRepository


class ListPetConsentSignaturesInteractor(ListPetConsentSignaturesUseCase):
    """그 아이의 서명들, 새것부터."""

    def __init__(self, pets: PetRepository, signatures: ConsentSignatureRepository) -> None:
        self._pets = pets
        self._signatures = signatures

    async def list_pet_consent_signatures(self, query: ListPetConsentSignaturesQuery) -> list[SignatureBriefView]:
        await self._pets.get(query.ctx, query.pet_id)   # 없는 아이·다른 매장의 아이는 404
        return [
            SignatureBriefView(s.signature_id, s.signed_at, s.channel, s.signer_name, s.parts)
            for s in await self._signatures.list_for_pet(query.ctx, query.pet_id)
        ]
