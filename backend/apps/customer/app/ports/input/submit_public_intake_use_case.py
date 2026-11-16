from __future__ import annotations

from abc import ABC, abstractmethod

from customer.app.dtos.public_form_dto import SubmitPublicIntakeCommand


class SubmitPublicIntakeUseCase(ABC):
    @abstractmethod
    async def submit_public_intake(self, command: SubmitPublicIntakeCommand) -> None: ...
