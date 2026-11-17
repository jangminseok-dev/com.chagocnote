from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.get_repeat_defaults_dto import GetRepeatDefaultsQuery, RepeatDefaultsView


class GetRepeatDefaultsUseCase(ABC):
    @abstractmethod
    async def get_repeat_defaults(self, query: GetRepeatDefaultsQuery) -> RepeatDefaultsView: ...
