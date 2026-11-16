from __future__ import annotations

from abc import ABC, abstractmethod

from guardian.app.dtos.family_dto import CreateFamilyInviteCommand, FamilyInviteResult


class CreateFamilyInviteUseCase(ABC):
    @abstractmethod
    async def create(self, command: CreateFamilyInviteCommand) -> FamilyInviteResult: ...
