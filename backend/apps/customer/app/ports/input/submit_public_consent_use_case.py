from __future__ import annotations

from abc import ABC, abstractmethod

from customer.app.dtos.public_form_dto import SubmitPublicConsentCommand


class SubmitPublicConsentUseCase(ABC):
    @abstractmethod
    async def submit_public_consent(self, command: SubmitPublicConsentCommand) -> None: ...
