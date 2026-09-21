from typing import Annotated

from pydantic import BaseModel, StringConstraints


class UpdateShopRequestSchema(BaseModel):
    """설정 화면의 폼 전체를 보낸다. 전화와 주소는 비우면 '없음'이 된다."""

    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    phone: Annotated[str, StringConstraints(strip_whitespace=True, max_length=20)] | None = None
    address: Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)] | None = None
