from __future__ import annotations

from abc import ABC, abstractmethod

from customer.app.dtos.consent_view_dto import FormLinkView
from customer.app.dtos.issue_intake_form_dto import IssueIntakeFormCommand


class IssueIntakeFormUseCase(ABC):
    @abstractmethod
    async def issue_intake_form(self, command: IssueIntakeFormCommand) -> FormLinkView: ...
