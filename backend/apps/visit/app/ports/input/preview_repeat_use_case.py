from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.preview_repeat_dto import PreviewRepeatQuery, RepeatPreviewView


class PreviewRepeatUseCase(ABC):
    @abstractmethod
    async def preview_repeat(self, query: PreviewRepeatQuery) -> RepeatPreviewView: ...
