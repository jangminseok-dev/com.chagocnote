"""규칙 기반 초안 해석 어댑터 — 도메인 서비스 draft_parser 를 그대로 부른다. LLM 어댑터의 자리다."""
from __future__ import annotations

from collections.abc import Sequence
from datetime import date, time

from visit.app.ports.output.visit_draft_parser_port import VisitDraftParserPort
from visit.domain.services.draft_parser import DraftParse, parse_draft


class RuleDraftParserAdapter(VisitDraftParserPort):
    def parse(
        self, text: str, today: date, opens_at: time, closes_at: time, menu_names: Sequence[str]
    ) -> DraftParse:
        return parse_draft(text, today, opens_at, closes_at, menu_names)
