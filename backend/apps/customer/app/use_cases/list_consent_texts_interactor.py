from __future__ import annotations

from customer.app.dtos.consent_text_view_dto import ConsentTextView
from customer.app.dtos.list_consent_texts_dto import ListConsentTextsQuery
from customer.app.ports.input.list_consent_texts_use_case import ListConsentTextsUseCase
from customer.app.ports.output.consent_text_repository import ConsentTextRepository
from customer.domain.services.consent_text import PARTS, default_body


def text_view(part: str, body: str | None) -> ConsentTextView:
    default = default_body(part)
    return ConsentTextView(part=part, body=body or default, edited=body is not None, default_body=default)


class ListConsentTextsInteractor(ListConsentTextsUseCase):
    """동의서의 토막 셋 — 지금 글과 기본 글. 고치지 않은 매장은 기본 글을 본다."""

    def __init__(self, texts: ConsentTextRepository) -> None:
        self._texts = texts

    async def list_consent_texts(self, query: ListConsentTextsQuery) -> list[ConsentTextView]:
        latest = await self._texts.latest(query.ctx)
        return [text_view(part, latest.get(part, (0, None))[1]) for part in PARTS]
