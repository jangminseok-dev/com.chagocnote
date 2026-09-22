"""API 프로세스 — 공개키로 토큰을 검증만 한다. 토큰을 발급할 수 없다."""
import os
import sys
from contextlib import asynccontextmanager

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "apps"))

from fastapi import FastAPI

from core.database import dispose_engine, init_engine
from core.redis import dispose_redis

from auth.adapter.inbound.api.error_map import AUTH_ERROR_STATUS
from auth.adapter.inbound.api.v1.get_me_router import get_me_router
from core.http_errors import install_error_handlers
from core.shop_guard import get_shop_access_port
from auth.dependencies.check_operator_provider import get_check_operator_use_case
from auth.dependencies.get_user_profiles_provider import get_get_user_profiles_use_case
from auth.dependencies.guard_active_user_provider import get_guard_active_user_use_case
from auth.dependencies.hub_ports import get_membership_directory
from customer.adapter.inbound.api.error_map import CUSTOMER_ERROR_STATUS
from customer.adapter.inbound.api.v1.customer_myself_router import customer_myself_router
from customer.adapter.inbound.api.v1.delete_customer_router import delete_customer_router
from customer.adapter.inbound.api.v1.get_customer_router import get_customer_router
from customer.adapter.inbound.api.v1.get_pet_router import get_pet_router
from customer.adapter.inbound.api.v1.list_pet_condition_types_router import (
    list_pet_condition_types_router,
)
from customer.adapter.inbound.api.v1.lookup_customer_router import lookup_customer_router
from customer.adapter.inbound.api.v1.register_customer_router import register_customer_router
from customer.adapter.inbound.api.v1.update_customer_router import update_customer_router
from platform_admin.adapter.inbound.api.error_map import PLATFORM_ADMIN_ERROR_STATUS
from platform_admin.adapter.inbound.api.v1.create_shop_router import create_shop_router
from platform_admin.adapter.inbound.api.v1.platform_myself_router import platform_myself_router
from platform_admin.dependencies.hub_ports import get_operator_directory, get_shop_provisioning
from tenancy.adapter.inbound.api.error_map import TENANCY_ERROR_STATUS
from tenancy.adapter.inbound.api.v1.accept_invite_router import accept_invite_router
from tenancy.adapter.inbound.api.v1.change_member_role_router import change_member_role_router
from tenancy.adapter.inbound.api.v1.create_invite_router import create_invite_router
from tenancy.adapter.inbound.api.v1.get_shop_router import get_shop_router
from tenancy.adapter.inbound.api.v1.list_members_router import list_members_router
from tenancy.adapter.inbound.api.v1.remove_member_router import remove_member_router
from tenancy.adapter.inbound.api.v1.tenancy_myself_router import tenancy_myself_router
from tenancy.adapter.inbound.api.v1.update_shop_router import update_shop_router
from tenancy.dependencies.hub_ports import get_active_user_guard, get_user_directory
from tenancy.dependencies.list_memberships_provider import get_list_memberships_use_case
from tenancy.dependencies.provision_shop_provider import get_provision_shop_use_case
from tenancy.dependencies.resolve_shop_access_provider import get_resolve_shop_access_use_case


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_engine()
    try:
        yield
    finally:
        await dispose_engine()
        await dispose_redis()


app = FastAPI(title="차곡노트 API", lifespan=lifespan)
app.include_router(get_me_router)
app.include_router(tenancy_myself_router)
app.include_router(accept_invite_router)
app.include_router(create_invite_router)
app.include_router(list_members_router)
app.include_router(change_member_role_router)
app.include_router(remove_member_router)
app.include_router(get_shop_router)
app.include_router(update_shop_router)
app.include_router(platform_myself_router)
app.include_router(create_shop_router)
# customer — /customers/myself 와 /customers/lookup 은 /customers/{customer_id} 보다 먼저 붙인다.
# 늦게 붙이면 {customer_id} 가 먼저 걸려 정수 변환 실패(422)가 된다.
app.include_router(customer_myself_router)
app.include_router(lookup_customer_router)
app.include_router(get_customer_router)
app.include_router(get_pet_router)
app.include_router(list_pet_condition_types_router)
app.include_router(register_customer_router)
app.include_router(update_customer_router)
app.include_router(delete_customer_router)
install_error_handlers(
    app,
    {
        **AUTH_ERROR_STATUS, **TENANCY_ERROR_STATUS, **PLATFORM_ADMIN_ERROR_STATUS,
        **CUSTOMER_ERROR_STATUS,
    },
)

# 허브 포트 조립 — 스포크끼리는 서로를 모른다. 소비하는 쪽의 "자리"에 구현하는 쪽의 프로바이더를 꽂는다.
app.dependency_overrides[get_shop_access_port] = get_resolve_shop_access_use_case
app.dependency_overrides[get_operator_directory] = get_check_operator_use_case
app.dependency_overrides[get_shop_provisioning] = get_provision_shop_use_case
app.dependency_overrides[get_user_directory] = get_get_user_profiles_use_case
app.dependency_overrides[get_membership_directory] = get_list_memberships_use_case
app.dependency_overrides[get_active_user_guard] = get_guard_active_user_use_case


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "process": "backend"}
