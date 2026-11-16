from __future__ import annotations

from abc import ABC, abstractmethod

from customer.app.dtos.consent_text_view_dto import ConsentTextView
from customer.app.dtos.list_consent_texts_dto import ListConsentTextsQuery


class ListConsentTextsUseCase(ABC):
    @abstractmethod
    async def list_consent_texts(self, query: ListConsentTextsQuery) -> list[ConsentTextView]: ...
