"""저장된 variables(구독자가 넣은 ISO 문자열)로 문안 변수와 문안을 만든다. 디스패처(보낼 때)와 API(share_text)가 같이 쓴다."""
from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime

from hub.app.dtos.customer_contact import CustomerContact
from hub.app.dtos.shop_context import ShopContext
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.shop_profile_port import ShopProfilePort
from notification.app.dtos.notification_message_dto import NotificationMessageView
from notification.domain.entities.notification_message import NotificationMessage
from notification.domain.services.templates import RenderedMessage, render, target_label, variables_for
from notification.domain.value_objects.message_status import FAILED


def _at(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def message_variables(kind: str, *, shop_name: str, target: str, tz: str, variables: Mapping[str, str]) -> dict[str, str]:
    """문안 변수(이름: 값, `#{}` 없음). 업체에 넘기는 사전이자 render 의 입력이다."""
    interval = variables.get("interval_weeks")
    return variables_for(
        kind, shop_name=shop_name, target=target, starts_at=datetime.fromisoformat(variables["starts_at"]), tz=tz,
        previous_starts_at=_at(variables.get("previous_starts_at")), url=variables.get("url"),
        expires_at=_at(variables.get("expires_at")), last_visit_at=_at(variables.get("completed_at")),
        interval_weeks=int(interval) if interval is not None else None,
    )


def message_text(kind: str, *, shop_name: str, target: str, tz: str, variables: Mapping[str, str]) -> RenderedMessage:
    return render(kind, message_variables(kind, shop_name=shop_name, target=target, tz=tz, variables=variables))


async def message_target(
    ctx: ShopContext, directory: CustomerDirectoryPort, message: NotificationMessage, contact: CustomerContact,
) -> str:
    """`#{대상}` — 반려동물 이름이 있으면 그것, 없으면 보호자 이름에 '님'. 보낼 때와 share_text 가 같은 재료로 만든다."""
    pet_name = None
    if message.pet_id is not None:
        pet = (await directory.briefs(ctx, [], [message.pet_id])).pets.get(message.pet_id)
        pet_name = pet.name if pet is not None else None
    return target_label(pet_name, contact.name)


async def message_views(
    ctx: ShopContext, messages: list[NotificationMessage], shops: ShopProfilePort, directory: CustomerDirectoryPort,
) -> list[NotificationMessageView]:
    """실패 줄에만 문자용 문안(share_text)을 붙인다 — 매장 이름·보호자·반려동물 이름은 지금 포트로 읽는다. 익명화됐으면 None."""
    profile = None
    views = []
    for m in messages:
        text = None
        if m.status == FAILED:
            if profile is None:
                profile = await shops.public_profile(ctx.shop_id)
            contact = await directory.contact(ctx, m.customer_id)
            if contact is not None:
                target = await message_target(ctx, directory, m, contact)
                text = message_text(m.kind, shop_name=profile.name, target=target, tz=ctx.timezone,
                                    variables=m.variables).sms_text
        views.append(NotificationMessageView(message=m, share_text=text))
    return views
