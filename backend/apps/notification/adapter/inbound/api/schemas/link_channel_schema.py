from __future__ import annotations

from pydantic import BaseModel

from notification.adapter.inbound.api.schemas.onboarding_fields import AdminPhone, CategoryCode, SearchId, SixDigits


class LinkChannelRequestSchema(BaseModel):
    """토큰 신청 때와 같은 셋 + 관리자 카카오톡으로 온 6자리."""

    search_id: SearchId
    admin_phone: AdminPhone
    category_code: CategoryCode
    token: SixDigits
