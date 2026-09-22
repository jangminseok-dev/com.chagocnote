"""customer 인터랙터 테스트가 함께 쓰는 폼 입력 — 라우터가 스키마에서 바꿔 넣는 모양 그대로다."""
from __future__ import annotations

from decimal import Decimal

from customer.app.dtos.customer_input_dto import CustomerInput, PetInput


def customer_input(**overrides) -> CustomerInput:
    fields = dict(name="김민지", phone="010-1234-5678", phone_alt=None, marketing_consent=False,
                  memo=None)
    fields.update(overrides)
    return CustomerInput(**fields)


def pet_input(**overrides) -> PetInput:
    fields = dict(
        name="콩이", species="dog", breed="말티즈", sex="female", neutered=True, birth_date=None,
        birth_year=2021, weight_kg=Decimal("3.2"), no_known_conditions=True, memo=None,
        conditions=(),
    )
    fields.update(overrides)
    return PetInput(**fields)
