"""템플릿 등록·검수 요청 — 연동(기본 5종)과 설정(다음 예약 제안을 처음 켤 때)이 함께 쓴다."""
from __future__ import annotations

import logging

from notification.app.ports.output.message_gateway_port import GatewayError, MessageGatewayPort
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
