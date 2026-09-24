from __future__ import annotations

from abc import ABC, abstractmethod

from media.app.dtos.issue_upload_dto import IssuedUploadView, IssueUploadCommand


class IssueUploadUseCase(ABC):
    @abstractmethod
    async def issue_upload(self, command: IssueUploadCommand) -> IssuedUploadView: ...
