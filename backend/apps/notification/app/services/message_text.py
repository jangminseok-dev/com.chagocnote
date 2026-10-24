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


def message_pet_ids(message: NotificationMessage) -> list[int]:
    """줄이 다루는 아이들 — variables 의 pet_ids(가족 묶음). 그 칸이 없는 줄(칸이 생기기 전 것)은 자기 pet_id 로."""
    listed = message.variables.get("pet_ids")
    if listed is None:
        return [message.pet_id] if message.pet_id is not None else []
    return [int(p) for p in listed.split(",") if p]


async def message_target(
    ctx: ShopContext, directory: CustomerDirectoryPort, message: NotificationMessage, contact: CustomerContact,
) -> str:
    """`#{대상}` — variables 의 pet_ids(가족 묶음)의 아이 이름을 '·' 로 잇는다(이름 없는 아이는 뺀다). 하나도 없으면
    보호자 이름에 '님'. pet_ids 가 없는 줄(이 칸이 생기기 전 것)은 자기 pet_id 로. 보낼 때와 share_text 가 같은 재료다."""
    pet_ids = message_pet_ids(message)
    pets = (await directory.briefs(ctx, [], pet_ids)).pets if pet_ids else {}
    names = [pets[p].name for p in pet_ids if p in pets and pets[p].name]
    return target_label("·".join(names), contact.name)


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
