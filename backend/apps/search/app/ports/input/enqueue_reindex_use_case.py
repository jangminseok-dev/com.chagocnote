from __future__ import annotations

from abc import ABC, abstractmethod

from search.app.dtos.enqueue_reindex_dto import EnqueueReindexCommand


class EnqueueReindexUseCase(ABC):
    @abstractmethod
    async def enqueue_reindex(self, command: EnqueueReindexCommand) -> None: ...
