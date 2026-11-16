from __future__ import annotations

from abc import ABC, abstractmethod

from customer.app.dtos.sign_consent_in_shop_dto import SignConsentInShopCommand


class SignConsentInShopUseCase(ABC):
    @abstractmethod
    async def sign_consent_in_shop(self, command: SignConsentInShopCommand) -> int: ...
