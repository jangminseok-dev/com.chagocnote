from __future__ import annotations

from abc import ABC, abstractmethod

from customer.app.dtos.delete_pet_dto import DeletePetCommand


class DeletePetUseCase(ABC):
    @abstractmethod
    async def delete_pet(self, command: DeletePetCommand) -> None: ...
