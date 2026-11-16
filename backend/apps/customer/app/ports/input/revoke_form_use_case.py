from __future__ import annotations

from abc import ABC, abstractmethod

from customer.app.dtos.revoke_form_dto import RevokeFormCommand


class RevokeFormUseCase(ABC):
    @abstractmethod
    async def revoke_form(self, command: RevokeFormCommand) -> None: ...
