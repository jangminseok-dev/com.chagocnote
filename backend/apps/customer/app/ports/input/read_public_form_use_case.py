from __future__ import annotations

from abc import ABC, abstractmethod

from customer.app.dtos.public_form_dto import PublicFormView, ReadPublicFormQuery


class ReadPublicFormUseCase(ABC):
    @abstractmethod
    async def read_public_form(self, query: ReadPublicFormQuery) -> PublicFormView: ...
