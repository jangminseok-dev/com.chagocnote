from __future__ import annotations

from abc import ABC, abstractmethod

from customer.app.dtos.consent_view_dto import SignatureBriefView
from customer.app.dtos.list_pet_consent_signatures_dto import ListPetConsentSignaturesQuery


class ListPetConsentSignaturesUseCase(ABC):
    @abstractmethod
    async def list_pet_consent_signatures(self, query: ListPetConsentSignaturesQuery) -> list[SignatureBriefView]: ...
