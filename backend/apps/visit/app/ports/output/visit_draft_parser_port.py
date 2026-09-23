from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import date, time

from visit.domain.services.draft_parser import DraftParse


class VisitDraftParserPort(ABC):
    """카톡 글 → 초안 해석. 지금 구현은 규칙 기반 도메인 서비스(외부 전송 없음)다.

    ⑨ 이후 LLM 어댑터로 바꿀 때 이 포트 뒤에서 어댑터만 바꾸고, 외부로 보내기 전 마스킹 Decorator 를 거친다(설계 13절).
    글은 여기서 해석만 하고 어디에도 남기지 않는다.
    """

    @abstractmethod
    def parse(
        self, text: str, today: date, opens_at: time, closes_at: time, menu_names: Sequence[str]
    ) -> DraftParse: ...
