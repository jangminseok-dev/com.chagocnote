from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.visit_events import VisitEvent


@dataclass(frozen=True)
class HandleVisitEventCommand:
    """visit 이 발행한 이벤트 하나. 매장 컨텍스트는 이벤트 안(event.ctx)에 있다."""

    event: VisitEvent
