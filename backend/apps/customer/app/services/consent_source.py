"""동의서의 기준값과 글을 매장의 설정에서 읽는다(⑪-B). 발급·문서 읽기·서명이 함께 쓴다."""
from __future__ import annotations

from dataclasses import dataclass

from customer.app.ports.output.consent_text_repository import ConsentTextRepository
from customer.app.ports.output.form_settings_repository import FormSettingsRepository
from customer.domain.entities.consent import ConsentPolicy
from customer.domain.services.consent_text import DEFAULT_VERSION, PARTS, default_body
from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class ConsentText:
    """토막 하나의 지금 글. source 는 default(차곡노트의 기본 글)·shop(매장이 고친 글)."""

    source: str
    version: int
    body: str


def default_texts() -> dict[str, ConsentText]:
    return {part: ConsentText("default", DEFAULT_VERSION, default_body(part)) for part in PARTS}


class ConsentSource:
    """저장소를 주지 않으면 기본값·기본 글이다(단위 테스트)."""

    def __init__(
        self, settings: FormSettingsRepository | None = None, texts: ConsentTextRepository | None = None,
    ) -> None:
        self._settings = settings
        self._texts = texts

    async def policy(self, ctx: ShopContext) -> ConsentPolicy:
        if self._settings is None:
            return ConsentPolicy()
        return (await self._settings.get(ctx)).policy

    async def texts(self, ctx: ShopContext) -> dict[str, ConsentText]:
        """토막별 지금 글. 매장이 고친 토막은 그 글, 고치지 않았거나 되돌린 토막은 기본 글의 최신 판이다."""
        found = default_texts()
        if self._texts is None:
            return found
        for part, (version, body) in (await self._texts.latest(ctx)).items():
            if body is not None:
                found[part] = ConsentText("shop", version, body)
        return found
