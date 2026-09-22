"""customer 라우터 테스트가 함께 쓰는 도우미 — 유스케이스와 매장 접근 확인을 스텁으로 바꾼 앱을 만든다."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import FastAPI

from core.database import get_db
from core.http_errors import install_error_handlers
from core.security import get_current_user_id
from core.shop_guard import get_shop_access_port
from customer.adapter.inbound.api.error_map import CUSTOMER_ERROR_STATUS
from customer.app.dtos.customer_view_dto import (
    CustomerDetailView,
    CustomerView,
    OwnerSummaryView,
    PetDetailView,
    PetView,
)
from customer.tests.helpers.profiles import OWNER_PERMISSIONS, STAFF_PERMISSIONS
from hub.app.dtos.shop_context import ShopContext

NOW = datetime(2026, 9, 22, 1, 0, tzinfo=timezone.utc)

class StubShopAccess:
    """ShopAccessPort 스텁 — 어느 매장이든 같은 역할·권한의 멤버로 통과시킨다."""

    def __init__(self, permissions=OWNER_PERMISSIONS, role="owner"):
        self.permissions = frozenset(permissions)
        self.role = role

    async def resolve(self, user_id, shop_id):
        return ShopContext(shop_id=shop_id, member_id=11, role=self.role, permissions=self.permissions)


STAFF = StubShopAccess(STAFF_PERMISSIONS, role="staff")
NO_WRITE = StubShopAccess(frozenset({"reservation:write"}), role="staff")


async def _no_db():
    yield None


def build_app(router, provider, stub_use_case, access=None, user_id=5) -> FastAPI:
    """access=None 이면 사장 권한으로 통과시킨다. user_id=None 이면 토큰 없는 요청이 된다."""
    app = FastAPI()
    app.include_router(router)
    install_error_handlers(app, CUSTOMER_ERROR_STATUS)
    app.dependency_overrides[provider] = lambda: stub_use_case
    app.dependency_overrides[get_db] = _no_db
    if user_id is not None:
        app.dependency_overrides[get_current_user_id] = lambda: user_id
    app.dependency_overrides[get_shop_access_port] = lambda: access or StubShopAccess()
    return app


def pet_view(pet_id=101, name="콩이") -> PetView:
    return PetView(
        pet_id=pet_id, customer_id=1, name=name, species="dog", breed="말티즈", sex="female",
        neutered=True, birth_date=None, birth_year=2021, age_label="5살", weight_kg=Decimal("3.2"),
        no_known_conditions=True, has_conditions=False, conditions=[], memo=None, passed_away_at=None,
    )


def customer_detail_view() -> CustomerDetailView:
    return CustomerDetailView(
        customer=CustomerView(customer_id=1, name="김민지", phone="01012345678", phone_alt=None,
                              marketing_consent=True, marketing_consent_changed_at=NOW, memo=None),
        pets=[pet_view()],
    )


def pet_detail_view() -> PetDetailView:
    return PetDetailView(
        pet=pet_view(),
        owner=OwnerSummaryView(customer_id=1, name="김민지", phone_masked="010-12··-5678"),
        siblings=[],
    )
