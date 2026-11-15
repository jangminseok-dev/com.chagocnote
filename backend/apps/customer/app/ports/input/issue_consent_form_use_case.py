from __future__ import annotations

from abc import ABC, abstractmethod

from customer.app.dtos.consent_view_dto import FormLinkView
from customer.app.dtos.issue_consent_form_dto import IssueConsentFormCommand


class IssueConsentFormUseCase(ABC):
    @abstractmethod
    async def issue_consent_form(self, command: IssueConsentFormCommand) -> FormLinkView: ...
