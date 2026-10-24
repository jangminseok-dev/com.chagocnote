from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from notification.adapter.inbound.api.schemas.onboarding_fields import AdminPhone, CategoryCode, SearchId


class RequestChannelTokenRequestSchema(BaseModel):
    """채널 검색 아이디·관리자 휴대폰·업종 카테고리. 다음 단계(연동)까지 앱이 든다 — 서버는 저장하지 않는다."""

    search_id: SearchId
    admin_phone: AdminPhone
    category_code: CategoryCode


class ChannelTokenRequestedSchema(BaseModel):
    status: Literal["token_requested"] = "token_requested"
