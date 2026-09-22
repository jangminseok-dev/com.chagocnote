"""customer 테스트가 함께 쓰는 값 — 매장 컨텍스트와 검증을 마친 보호자·반려동물 정보."""
from __future__ import annotations

from decimal import Decimal

from customer.domain.value_objects.condition_entry import ConditionEntry
from customer.domain.value_objects.customer_profile import CustomerProfile
from customer.domain.value_objects.pet_profile import PetProfile
from hub.app.dtos.shop_context import ShopContext

STAFF_PERMISSIONS = frozenset({"reservation:write", "customer:write", "record:write", "sales:write"})
OWNER_PERMISSIONS = STAFF_PERMISSIONS | frozenset(
    {"sales:read", "record:delete", "customer:delete", "member:manage", "shop:update"}
)


def ctx(shop_id: int = 1, member_id: int = 11, role: str = "owner") -> ShopContext:
    permissions = OWNER_PERMISSIONS if role == "owner" else STAFF_PERMISSIONS
    return ShopContext(shop_id=shop_id, member_id=member_id, role=role, permissions=permissions)


def customer_profile(**overrides) -> CustomerProfile:
    fields = dict(name="김민지", phone="01012345678", phone_alt=None, marketing_consent=False,
                  memo=None)
    fields.update(overrides)
    return CustomerProfile(**fields)


def pet_profile(**overrides) -> PetProfile:
    fields = dict(
        name="콩이", species="dog", breed="말티즈", sex="female", neutered=True, birth_date=None,
        birth_year=2021, weight_kg=Decimal("3.2"), no_known_conditions=True, memo=None,
        conditions=(),
    )
    fields.update(overrides)
    return PetProfile(**fields)


def condition(type_code: str, custom_label: str | None = None, note: str | None = None) -> ConditionEntry:
    return ConditionEntry(type_code=type_code, custom_label=custom_label, note=note)
