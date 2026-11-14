"""미용 동의·주의 표시의 쓰기 넷 — 경로, 권한, 본문, 응답의 칸."""
from datetime import date

import pytest
from httpx import ASGITransport, AsyncClient

from customer.adapter.inbound.api.v1.clear_customer_caution_router import clear_customer_caution_router
from customer.adapter.inbound.api.v1.clear_pet_grooming_consent_router import clear_pet_grooming_consent_router
from customer.adapter.inbound.api.v1.set_customer_caution_router import set_customer_caution_router
from customer.adapter.inbound.api.v1.set_pet_grooming_consent_router import set_pet_grooming_consent_router
from customer.dependencies.clear_customer_caution_provider import get_clear_customer_caution_use_case
from customer.dependencies.clear_pet_grooming_consent_provider import get_clear_pet_grooming_consent_use_case
from customer.dependencies.set_customer_caution_provider import get_set_customer_caution_use_case
from customer.dependencies.set_pet_grooming_consent_provider import get_set_pet_grooming_consent_use_case
from customer.tests.helpers.api import NO_WRITE, STAFF, build_app, customer_detail_view, pet_detail_view


class _Stub:
    """네 유스케이스를 한 스텁이 받는다 — 받은 명령을 적어 둔다."""

    def __init__(self):
        self.commands = []

    async def set_pet_grooming_consent(self, command):
        self.commands.append(command)
        return pet_detail_view()

    clear_pet_grooming_consent = set_pet_grooming_consent

    async def set_customer_caution(self, command):
        self.commands.append(command)
        return customer_detail_view()

    clear_customer_caution = set_customer_caution


CASES = {
    "consent": (set_pet_grooming_consent_router, get_set_pet_grooming_consent_use_case,
                "PUT", "/v1/shops/3/pets/101/grooming-consent", {}),
    "consent_clear": (clear_pet_grooming_consent_router, get_clear_pet_grooming_consent_use_case,
                      "DELETE", "/v1/shops/3/pets/101/grooming-consent", None),
    "caution": (set_customer_caution_router, get_set_customer_caution_use_case,
                "PUT", "/v1/shops/3/customers/7/caution", {"reason": "노쇼 2번"}),
    "caution_clear": (clear_customer_caution_router, get_clear_customer_caution_use_case,
                      "DELETE", "/v1/shops/3/customers/7/caution", None),
}


async def _call(case, stub, access=None, body="default", user_id=5):
    router, provider, method, path, default = CASES[case]
    app = build_app(router, provider, stub, access=access, user_id=user_id)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        payload = default if body == "default" else body
        return await client.request(method, path, json=payload) if payload is not None else await client.request(method, path)


@pytest.mark.parametrize("case", CASES)
async def test_직원도_쓰고_customer_write_가_없으면_403_이다(case):
    stub = _Stub()
    assert (await _call(case, stub, STAFF)).status_code == 200
    assert len(stub.commands) == 1
    denied = await _call(case, _Stub(), NO_WRITE)
    assert (denied.status_code, denied.json()["code"]) == (403, "PERMISSION_DENIED")


@pytest.mark.parametrize("case", CASES)
async def test_토큰이_없으면_401_이다(case):
    assert (await _call(case, _Stub(), user_id=None)).status_code == 401


async def test_동의의_받은_날은_있으면_그_날_없으면_None_으로_넘긴다():
    stub = _Stub()
    await _call("consent", stub, body={"received_on": "2026-03-01"})
    await _call("consent", stub, body={})
    assert [(c.pet_id, c.received_on) for c in stub.commands] == [(101, date(2026, 3, 1)), (101, None)]


@pytest.mark.parametrize("body", [{"received_on": "어제"}, {"received_on": "2026-02-31"}, {"received_on": 20260301}])
async def test_날짜가_아닌_받은_날은_422_다(body):
    stub = _Stub()
    assert (await _call("consent", stub, body=body)).status_code == 422
    assert stub.commands == []


async def test_주의의_사유를_그대로_넘기고_본문이_없거나_너무_길면_422_다():
    stub = _Stub()
    await _call("caution", stub, body={"reason": " 입질 "})
    assert (stub.commands[0].customer_id, stub.commands[0].reason) == (7, " 입질 ")   # 다듬기는 도메인이 한다
    for body in ({}, {"reason": None}, {"reason": 3}, {"reason": "가" * 301}):
        response = await _call("caution", _Stub(), body=body)
        assert response.status_code == 422
        assert "가가가" not in response.text   # 사유를 오류 본문에 되돌려 싣지 않는다


async def test_응답에_동의_받은_날과_주의_칸이_있다():
    pet = (await _call("consent", _Stub())).json()
    assert pet["pet"]["grooming_consent_on"] is None and pet["caution"] is None
    customer = (await _call("caution", _Stub())).json()
    assert customer["customer"]["caution"] is None


@pytest.mark.parametrize("reason", ["입질\u0000", "노쇼\n\n2번", "노쇼\t2번", "\u0007벨", "줄\r바꿈"])
async def test_주의_사유의_제어_문자는_422_다(reason):
    """NUL 은 DB 가 받지 못해 500 이 되고, 개행·탭은 한 줄 문구를 깨뜨린다 — 다른 글자 입력처럼 문 앞에서 막는다."""
    stub = _Stub()
    response = await _call("caution", stub, body={"reason": reason})
    assert response.status_code == 422
    assert stub.commands == []
