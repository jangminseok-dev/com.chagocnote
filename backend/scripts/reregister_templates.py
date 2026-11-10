"""반려됐거나 문안 판이 바뀐 템플릿을 연동된 매장마다 새 판으로 등록·검수 요청한다(설계 6.2·7.4). 여러 번 돌려도 결과가 같다.

기본: 연동된 모든 매장(또는 --shop 하나)에서 코드의 TEXT_VERSION 이 DB 의 본 판(text_version)도 심사 중인 새 판
(pending_text_version)도 아니거나 rejected 인 종류를 새 판으로 등록한다(없는 종류도 등록한다 — 디스패처의 10분 주기와
같은 일). next_visit 은 설정에서 켠 매장만. 승인된 종류는 덮지 않는다 — 새 판은 대기 칸에 들고 심사가 끝날 때까지 옛
판으로 계속 나간다(설계 2026-11-10 3.2). 새 판이 반려되면 옛 판이 남으므로 문안을 고친 뒤 다시 돌린다.
--refresh: 등록 대신 심사 중인 템플릿(첫 판 pending, 승인된 줄의 대기 판)의 업체 상태만 조회해 적는다(디스패처의 10분
주기를 바로 당긴다 — 흐름 스크립트가 쓴다). 새 판이 반려되면 결과는 rejected_new_version 이다.
종류마다 업체를 먼저 부르고 그 뒤 저장·커밋한다 — 잠금을 쥔 채 업체를 부르지 않는다(N14).
출력은 매장 ID·종류·결과만이다. 업체 ID·오류 본문·번호는 찍지 않는다(N12).
사용: cd infra && docker compose run --rm backend python scripts/reregister_templates.py [--shop <id>] [--refresh]
"""
from __future__ import annotations

import argparse
import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from core.config import DATABASE_URL
from notification.app.ports.output.message_gateway_port import GatewayError, MessageGatewayPort
from notification.app.ports.output.notification_queue_repository import NotificationQueueRepository
from notification.app.ports.output.settings_repository import SettingsRepository
from notification.app.ports.output.template_repository import TemplateRepository
from notification.app.services.system_context import system_context
from notification.app.services.template_registration import record_template_state
from notification.dependencies.notification_wiring import (
    build_message_repository,
    build_settings_repository,
    build_template_repository,
    get_message_gateway,
)
from notification.domain.services.templates import TEMPLATES, TEXT_VERSION
from notification.domain.value_objects.message_kind import DEFAULT_KINDS, NEXT_VISIT
from notification.domain.value_objects.template_status import PENDING, REJECTED

Commit = Callable[[], Awaitable[None]]
# (매장 ID, 종류, 결과) — "registered" · "approved" · "rejected" · "rejected_new_version" · "pending" · "failed(<코드>)"
Result = tuple[int, str, str]


async def reregister(
    queue: NotificationQueueRepository, settings: SettingsRepository, templates: TemplateRepository,
    gateway: MessageGatewayPort, commit: Commit, now: datetime, shop_id: int | None = None,
) -> list[Result]:
    """새 판이 필요한 종류를 등록·검수 요청하고 pending 으로 적는다. 업체 오류는 그 종류만 건너뛴다."""
    results: list[Result] = []
    channels = [c for c in await queue.list_linked_channels() if shop_id is None or c.shop_id == shop_id]
    existing = await queue.list_templates_for_shops([c.shop_id for c in channels])
    for channel in channels:
        ctx = system_context(channel.shop_id)
        current = await settings.get(ctx)
        wanted = list(DEFAULT_KINDS)
        if current is not None and current.next_visit_enabled:
            wanted.append(NEXT_VISIT)
        have = {t.kind: t for t in existing[channel.shop_id]}
        for kind in wanted:
            template = have.get(kind)
            if (template is not None and template.status != REJECTED
                    and TEXT_VERSION in (template.text_version, template.pending_text_version)):
                continue
            try:
                provider_id = await gateway.register_template(channel.provider_channel_id, TEMPLATES[kind], TEXT_VERSION)
            except GatewayError as exc:
                results.append((channel.shop_id, kind, f"failed({exc.code})"))
                continue
            await templates.upsert(ctx, kind, TEXT_VERSION, provider_id, now)
            await commit()
            results.append((channel.shop_id, kind, "registered"))
    return results


async def refresh_pending(
    queue: NotificationQueueRepository, templates: TemplateRepository, gateway: MessageGatewayPort, commit: Commit,
    now: datetime, shop_id: int | None = None,
) -> list[Result]:
    """심사 중인 템플릿의 업체 상태를 물어 결과가 났으면 적는다. 등록은 하지 않는다."""
    results: list[Result] = []
    for template in await queue.list_pending_templates():
        if shop_id is not None and template.shop_id != shop_id:
            continue
        try:
            state = await gateway.template_state(template.review_provider_template_id)
        except GatewayError as exc:
            results.append((template.shop_id, template.kind, f"failed({exc.code})"))
            continue
        recorded = await record_template_state(templates, system_context(template.shop_id), template, state, now)
        if recorded is not None:
            await commit()
        results.append((template.shop_id, template.kind, recorded or PENDING))
    return results


async def run(
    *, queue: NotificationQueueRepository, settings: SettingsRepository, templates: TemplateRepository,
    gateway: MessageGatewayPort, commit: Commit, now: datetime, shop_id: int | None, refresh: bool,
) -> list[Result]:
    if refresh:
        return await refresh_pending(queue, templates, gateway, commit, now, shop_id)
    return await reregister(queue, settings, templates, gateway, commit, now, shop_id)


async def _run(shop_id: int | None, refresh: bool) -> list[Result]:
    engine = create_async_engine(DATABASE_URL, hide_parameters=True)
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            messages = build_message_repository(session)
            return await run(
                queue=messages, settings=build_settings_repository(session), templates=build_template_repository(session),
                gateway=get_message_gateway(), commit=session.commit, now=datetime.now(timezone.utc),
                shop_id=shop_id, refresh=refresh,
            )
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="알림톡 템플릿 재등록(기본) 또는 심사 상태 조회(--refresh)")
    parser.add_argument("--shop", type=int, default=None, help="이 매장만(기본: 연동된 모든 매장)")
    parser.add_argument("--refresh", action="store_true", help="등록 대신 pending 템플릿의 업체 상태만 조회해 적는다")
    args = parser.parse_args()
    results = asyncio.run(_run(args.shop, args.refresh))
    for shop_id, kind, result in results:
        print(f"매장 {shop_id} {kind} {result}")
    print(f"{'상태 조회' if args.refresh else '재등록'} {len(results)}건.")


if __name__ == "__main__":
    main()
