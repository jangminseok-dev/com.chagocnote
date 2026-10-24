from __future__ import annotations

from abc import ABC, abstractmethod

from notification.app.dtos.request_sender_verification_dto import RequestSenderVerificationCommand


class RequestSenderVerificationUseCase(ABC):
    @abstractmethod
    async def request_sender_verification(self, command: RequestSenderVerificationCommand) -> None: ...
