"""notification 경로 변수. bigint 를 넘는 값은 DB 에 닿기 전에 422 로 막고, 종류는 여섯 중 하나여야 한다."""
from typing import Annotated

from fastapi import Path

from notification.domain.value_objects.message_kind import KINDS

_MAX_BIGINT = 9_223_372_036_854_775_807

VisitId = Annotated[int, Path(ge=1, le=_MAX_BIGINT)]
MessageId = Annotated[int, Path(ge=1, le=_MAX_BIGINT)]
MessageKind = Annotated[str, Path(pattern=f"^({'|'.join(KINDS)})$")]
