from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field

from visit.adapter.inbound.api.schemas.register_visit_schema import EntityId
from visit.domain.services.report_rules import MAX_HIDDEN


class SendVisitReportRequestSchema(BaseModel):
    """뺄 사진·영상 전부를 보낸다(없으면 빈 배열). 응답은 미리보기와 같은 모양(VisitReportSchema)이다.

    개수 상한은 요청 하나가 큰 일을 시키지 못하게 하는 입력 경계다. 이 기록의 것이 아닌 ID 와 중복은
    도메인이 거른다(422 VALIDATION_ERROR).
    """

    hidden_media_ids: Annotated[list[EntityId], Field(max_length=MAX_HIDDEN)]
