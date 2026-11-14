from __future__ import annotations

from typing import Annotated

from pydantic import AfterValidator, BaseModel, StringConstraints

from customer.adapter.inbound.api.schemas.text_validators import reject_control_chars


class SetCustomerCautionRequestSchema(BaseModel):
    # 길이의 정확한 판정(앞뒤 공백을 뗀 뒤 1~100자)은 도메인이 한다. 여기서는 터무니없이 긴 본문과 제어 문자
    # (NUL 은 DB 가 받지 못하고, 개행·탭은 한 줄 문구를 깨뜨린다)만 막는다. 사유는 한 줄이다.
    reason: Annotated[str, StringConstraints(max_length=300), AfterValidator(reject_control_chars)]
