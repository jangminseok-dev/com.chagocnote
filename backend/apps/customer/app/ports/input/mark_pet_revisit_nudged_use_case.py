from __future__ import annotations

from abc import ABC, abstractmethod

from customer.app.dtos.mark_pet_revisit_nudged_dto import MarkPetRevisitNudgedCommand


class MarkPetRevisitNudgedUseCase(ABC):
    @abstractmethod
    async def mark_pet_revisit_nudged(self, command: MarkPetRevisitNudgedCommand) -> None: ...
