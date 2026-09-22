from httpx import ASGITransport, AsyncClient

from customer.adapter.inbound.api.v1.register_customer_router import register_customer_router
from customer.dependencies.register_customer_provider import get_register_customer_use_case
from customer.tests.helpers.api import (
    CUSTOMER_BODY,
    NO_WRITE,
    PET_BODY,
    STAFF,
    build_app,
    customer_detail_view,
)


class _StubUseCase:
    def __init__(self):
        self.commands = []

    async def register_customer(self, command):
        self.commands.append(command)
        return customer_detail_view()


async def _post(stub, body, access=None):
    app = build_app(register_customer_router, get_register_customer_use_case, stub, access=access)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        return await client.post("/v1/shops/3/customers", json=body)


async def test_직원도_등록하고_201_과_고객_상세를_받는다():
    stub = _StubUseCase()
    response = await _post(stub, {"customer": CUSTOMER_BODY, "pet": PET_BODY}, access=STAFF)
    assert response.status_code == 201
    assert response.json()["customer"]["phone"] == "01012345678"
    assert response.json()["pets"][0]["weight_kg"] == 3.2   # 문자열이 아니라 숫자로 나간다
    command = stub.commands[0]
    assert command.ctx.shop_id == 3
    # 앞뒤 공백을 없애고 빈 문자열은 None 으로 바꾼다. 전화번호 정규화는 유스케이스가 한다.
    assert (command.customer.name, command.customer.phone, command.customer.phone_alt,
            command.customer.memo) == ("김민지", "010-1234-5678", None, None)
    assert command.pet.conditions[0].custom_label == "눈물 자국"
    assert command.pet.conditions[0].note is None


async def test_customer_write_가_없으면_403_이다():
    stub = _StubUseCase()
    response = await _post(stub, {"customer": CUSTOMER_BODY, "pet": PET_BODY}, access=NO_WRITE)
    assert (response.status_code, response.json()["code"]) == (403, "PERMISSION_DENIED")
    assert stub.commands == []


async def test_형식이_틀리면_422_VALIDATION_ERROR_다():
    cases = [
        {"customer": CUSTOMER_BODY},                                                    # 반려동물 없음
        {"customer": {**CUSTOMER_BODY, "name": "  "}, "pet": PET_BODY},                 # 빈 이름
        {"customer": {**CUSTOMER_BODY, "marketing_consent": "true"}, "pet": PET_BODY},  # 문자열 불리언
        {"customer": {**CUSTOMER_BODY, "marketing_consent": None}, "pet": PET_BODY},    # 동의는 필수 선택
        {"customer": CUSTOMER_BODY, "pet": {**PET_BODY, "species": "bird"}},
        {"customer": CUSTOMER_BODY, "pet": {**PET_BODY, "sex": "unknown"}},
        {"customer": CUSTOMER_BODY, "pet": {**PET_BODY, "weight_kg": 0}},
        {"customer": CUSTOMER_BODY, "pet": {**PET_BODY, "weight_kg": 3.25}},           # 소수 한 자리
        {"customer": CUSTOMER_BODY, "pet": {**PET_BODY, "weight_kg": 1000}},           # numeric(4,1)
        {"customer": CUSTOMER_BODY, "pet": {**PET_BODY, "name": "가" * 51}},
        {"customer": CUSTOMER_BODY, "pet": {**PET_BODY, "memo": "가" * 501}},
        {"customer": CUSTOMER_BODY, "pet": {**PET_BODY, "conditions": [{"type_code": "other", "custom_label": "가" * 31}]}},
        {"customer": {**CUSTOMER_BODY, "name": "김민지\u0000"}, "pet": PET_BODY},  # NUL 문자
        {"customer": CUSTOMER_BODY, "pet": {**PET_BODY, "breed": "말티즈\x01"}},   # 제어 문자
    ]
    for body in cases:
        response = await _post(_StubUseCase(), body)
        assert (response.status_code, response.json()["code"]) == (422, "VALIDATION_ERROR"), body


async def test_메모의_개행은_허용된다():
    stub = _StubUseCase()
    body = {"customer": {**CUSTOMER_BODY, "memo": "1차\n2차"}, "pet": PET_BODY}
    response = await _post(stub, body)
    assert response.status_code == 201
    assert stub.commands[0].customer.memo == "1차\n2차"
