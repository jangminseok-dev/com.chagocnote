"""공개 서류의 관문 — 토큰이 가리키는 요청과 영업 중인 매장(⑪ 설계 3.1). 읽기와 제출이 함께 쓴다.

알림장의 관문과 같은 순서다. 닫힌 이유(끊음·기간 지남·매장 정지)는 가르지 않고 오류에 요청·매장의 값을 싣지 않는다.
낸 요청은 여기서 떨어뜨리지 않는다 — 읽기가 "보냈어요"를 보여야 한다.
"""
from __future__ import annotations

from datetime import datetime

from core.link_token import read_token
from customer.app.ports.output.consent_form_repository import ConsentFormRepository
from customer.app.services.consent_forms import FORM_PURPOSE
from customer.domain.entities.consent_form import ConsentForm
from customer.domain.errors import FormClosedError, FormNotFoundError, TooManyFormRequestsError
from hub.app.dtos.shop_profile import ShopProfile
from hub.app.ports.public_limiter_port import PublicLimiterPort
from hub.app.ports.shop_profile_port import ShopProfilePort


async def open_form(
    token: str | None, client: str, now: datetime, *, link_key: bytes, forms: ConsentFormRepository,
    shops: ShopProfilePort, limiter: PublicLimiterPort,
) -> tuple[ConsentForm, ShopProfile]:
    if not await limiter.allow(client):
        raise TooManyFormRequestsError("요청이 너무 잦습니다. 잠시 뒤에 다시 열어 주세요.")
    # 서명을 확인한 public_id 로만 DB 를 읽는다. 서명이 틀리면(추측 시도) 실패 수 차단을 본다 —
    # 서명이 맞는 토큰은 남의 실패로 막히지 않는다. 알림장 토큰은 용도가 달라 여기서 떨어진다.
    public_id = read_token(token, link_key, FORM_PURPOSE)
    if public_id is None:
        if await limiter.missed_too_much(client):
            raise TooManyFormRequestsError("요청이 너무 잦습니다. 잠시 뒤에 다시 열어 주세요.")
        await limiter.note_miss(client)
        raise FormNotFoundError("서류를 찾을 수 없습니다.")
    form = await forms.find_public(public_id)
    if form is None:
        await limiter.note_miss(client)
        raise FormNotFoundError("서류를 찾을 수 없습니다.")
    if form.is_closed(now):
        raise FormClosedError("닫힌 서류입니다.")
    shop = await shops.public_profile(form.shop_id)
    if shop is None or not shop.open:
        raise FormClosedError("닫힌 서류입니다.")
    return form, shop
