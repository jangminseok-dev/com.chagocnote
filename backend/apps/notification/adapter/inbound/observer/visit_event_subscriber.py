"""Observer — core/observer 버스에 등록되는 구독자. main.py 가 import 때 subscribe 로 꽂는다(설계 3.1·3.3).

발행한 visit 인터랙터와 같은 세션·같은 트랜잭션에서 돈다 — 구독자가 던지면 방문 저장도 롤백된다(N13).
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from hub.app.dtos.visit_events import VisitEvent
from notification.adapter.outbound.pg.channel_pg_repository import ChannelPgRepository
from notification.adapter.outbound.pg.message_pg_repository import MessagePgRepository
from notification.adapter.outbound.pg.settings_pg_repository import SettingsPgRepository
from notification.adapter.outbound.pg.template_pg_repository import TemplatePgRepository
from notification.app.dtos.handle_visit_event_dto import HandleVisitEventCommand
from notification.app.services.dispatcher_wakeup import wake
from notification.app.use_cases.handle_visit_event_interactor import HandleVisitEventInteractor
from notification.domain.services.clock import utc_now


async def handle_visit_event(session: AsyncSession, event: VisitEvent) -> None:
    """요청의 세션으로 저장소를 만들어 인터랙터를 부른다. 이벤트를 로그에 남기지 않는다(알림장 주소가 든다, N12)."""
    use_case = HandleVisitEventInteractor(
        channels=ChannelPgRepository(session), settings=SettingsPgRepository(session),
        templates=TemplatePgRepository(session), messages=MessagePgRepository(session), now=utc_now,
    )
    await use_case.handle_visit_event(HandleVisitEventCommand(event=event))
    wake()   # 줄을 만들었든 아니든 — 루프가 반 초 뒤(요청의 커밋 뒤) 돈다(설계 5.3-1)
