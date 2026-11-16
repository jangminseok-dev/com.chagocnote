from __future__ import annotations

from abc import ABC, abstractmethod

from customer.app.dtos.consent_view_dto import SentFormView
from customer.app.dtos.list_forms_dto import ListFormsQuery


class ListFormsUseCase(ABC):
    @abstractmethod
    async def list_forms(self, query: ListFormsQuery) -> list[SentFormView]: ...
