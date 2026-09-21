from __future__ import annotations

from abc import ABC, abstractmethod

from tenancy.app.dtos.create_invite_dto import CreatedInvite, CreateInviteCommand


class CreateInviteUseCase(ABC):
    @abstractmethod
    async def create(self, command: CreateInviteCommand) -> CreatedInvite: ...
