from __future__ import annotations

from abc import ABC, abstractmethod

from customer.app.dtos.consent_text_view_dto import ConsentTextView
from customer.app.dtos.update_consent_text_dto import UpdateConsentTextCommand


class UpdateConsentTextUseCase(ABC):
    @abstractmethod
    async def update_consent_text(self, command: UpdateConsentTextCommand) -> ConsentTextView: ...
