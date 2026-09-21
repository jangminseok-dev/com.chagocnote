from __future__ import annotations

from abc import ABC, abstractmethod

from tenancy.app.dtos.accept_invite_dto import AcceptInviteCommand, AcceptInviteResult


class AcceptInviteUseCase(ABC):
    @abstractmethod
    async def accept(self, command: AcceptInviteCommand) -> AcceptInviteResult: ...
