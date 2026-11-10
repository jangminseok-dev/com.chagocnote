"""템플릿 등록·검수 요청 — 연동(기본 5종)과 설정(다음 예약 제안을 처음 켤 때)이 함께 쓴다. 심사 결과 적기는 디스패처의
10분 주기와 운영자 스크립트(--refresh)가 함께 쓴다."""
from __future__ import annotations

import logging
from datetime import datetime

from hub.app.dtos.shop_context import ShopContext
from notification.app.ports.output.message_gateway_port import GatewayError, MessageGatewayPort, TemplateState
from notification.app.ports.output.template_repository import TemplateRepository
from notification.domain.entities.notification_template import NotificationTemplate
from notification.domain.value_objects.template_status import APPROVED, REJECTED
from notification.domain.services.templates import TEMPLATES, TEXT_VERSION

logger = logging.getLogger("notification.onboarding")


async def register_template(gateway: MessageGatewayPort, provider_channel_id: str, kind: str) -> str | None:
    """업체에 등록하고 업체 템플릿 ID 를 돌려준다. 업체 오류면 WARNING 만 남기고 None — 디스패처의 10분 주기가 다시
    등록한다(설계 9.5). 잠금을 쥐기 전에 부른다(N14)."""
    try:
        return await gateway.register_template(provider_channel_id, TEMPLATES[kind], TEXT_VERSION)
    except GatewayError as exc:
        logger.warning("%s 템플릿 등록 실패 (%s) — 디스패처가 다시 등록합니다", kind, exc.code)
        return None


REJECTED_NEW_VERSION = "rejected_new_version"


async def record_template_state(
    templates: TemplateRepository, ctx: ShopContext, template: NotificationTemplate, state: TemplateState, now: datetime
) -> str | None:
    """업체가 준 심사 상태를 적는다. 아직 심사 중이면 None. 첫 판이면 status 로 적고 "approved"/"rejected". 승인된 줄에
    걸린 새 판(대기 칸)이면 승인은 본 칸으로 올리고 "approved", 반려는 옛 판을 둔 채 대기 칸만 비우고
    "rejected_new_version"(설계 2026-11-10 3.2)."""
    if state.status not in (APPROVED, REJECTED):
        return None
    if template.pending_provider_template_id is None:
        await templates.set_status(ctx, template.kind, state.status, state.rejected_reason, now)
        return state.status
    approved = state.status == APPROVED
    await templates.decide_pending(ctx, template.kind, approved, state.rejected_reason, now)
    return APPROVED if approved else REJECTED_NEW_VERSION
