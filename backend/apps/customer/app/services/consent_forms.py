"""동의서 요청의 작은 규칙들 — 주소 만들기와, 서명·삭제로 아이가 빠질 때 살아 있는 요청 고치기."""
from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from core.link_token import make_token
from customer.app.ports.output.consent_form_repository import ConsentFormRepository
from customer.domain.entities.consent_form import ConsentForm
from hub.app.dtos.shop_context import ShopContext

FORM_PURPOSE = b"form:"   # 알림장 토큰과 서로의 경로에서 읽히지 않게 가르는 말


def form_url(form: ConsentForm, *, link_key: bytes, web_base_url: str) -> str:
    """보호자가 여는 주소. 로그·오류 메시지에 남기지 않는다."""
    return f"{web_base_url}/f/{make_token(form.public_id, link_key, FORM_PURPOSE)}"


async def drop_pets(
    ctx: ShopContext, customer_id: int, pet_ids: Iterable[int], now: datetime, forms: ConsentFormRepository,
) -> None:
    """그 고객의 살아 있는 요청에서 아이들을 덜어 낸다. 아이가 남지 않은 요청은 끊는다.

    고객 행을 이미 쥔 안에서 부른다(잠금 순서: 고객 행 → 서류 요청 행).
    """
    gone = set(pet_ids)
    for form in await forms.live_for_customer(ctx, customer_id, now):
        left = tuple(pet_id for pet_id in form.pet_ids if pet_id not in gone)
        if left == form.pet_ids:
            continue
        if left:
            await forms.set_pets(ctx, form.id, left)
        else:
            await forms.revoke(ctx, form.id, now)
