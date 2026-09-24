"""API 프로세스 — 공개키로 토큰을 검증만 한다. 토큰을 발급할 수 없다."""
import os
import sys
from contextlib import asynccontextmanager

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "apps"))

from fastapi import FastAPI

from core.access_log import redact_access_log_queries
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
from customer.adapter.inbound.api.v1.add_pet_router import add_pet_router
from customer.adapter.inbound.api.v1.customer_myself_router import customer_myself_router
from customer.adapter.inbound.api.v1.delete_customer_router import delete_customer_router
from customer.adapter.inbound.api.v1.delete_pet_router import delete_pet_router
from customer.adapter.inbound.api.v1.get_customer_router import get_customer_router
from customer.adapter.inbound.api.v1.get_pet_router import get_pet_router
from customer.adapter.inbound.api.v1.list_customers_router import list_customers_router
from customer.adapter.inbound.api.v1.list_pet_condition_types_router import (
    list_pet_condition_types_router,
)
from customer.adapter.inbound.api.v1.lookup_customer_router import lookup_customer_router
from customer.adapter.inbound.api.v1.mark_pet_passed_away_router import mark_pet_passed_away_router
from customer.adapter.inbound.api.v1.register_customer_router import register_customer_router
from customer.adapter.inbound.api.v1.unmark_pet_passed_away_router import (
    unmark_pet_passed_away_router,
)
from customer.adapter.inbound.api.v1.update_customer_router import update_customer_router
from customer.adapter.inbound.api.v1.update_pet_router import update_pet_router
from customer.dependencies.customer_directory_provider import get_customer_directory_use_case
from customer.dependencies.hub_ports import get_visit_ledger
from media.adapter.inbound.api.error_map import MEDIA_ERROR_STATUS
from media.adapter.inbound.api.v1.confirm_upload_router import confirm_upload_router
from media.adapter.inbound.api.v1.issue_upload_router import issue_upload_router
from media.adapter.inbound.api.v1.media_myself_router import media_myself_router
from media.dependencies.media_library_provider import get_media_library_use_case
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
from visit.adapter.inbound.api.error_map import VISIT_ERROR_STATUS
from visit.adapter.inbound.api.v1.add_closed_date_router import add_closed_date_router
from visit.adapter.inbound.api.v1.archive_menu_router import archive_menu_router
from visit.adapter.inbound.api.v1.create_menu_router import create_menu_router
from visit.adapter.inbound.api.v1.delete_closed_date_router import delete_closed_date_router
from visit.adapter.inbound.api.v1.get_next_visit_draft_router import get_next_visit_draft_router
from visit.adapter.inbound.api.v1.get_visit_calendar_router import get_visit_calendar_router
from visit.adapter.inbound.api.v1.get_visit_defaults_router import get_visit_defaults_router
from visit.adapter.inbound.api.v1.get_visit_router import get_visit_router
from visit.adapter.inbound.api.v1.get_visit_settings_router import get_visit_settings_router
from visit.adapter.inbound.api.v1.list_closed_dates_router import list_closed_dates_router
from visit.adapter.inbound.api.v1.list_day_visits_router import list_day_visits_router
from visit.adapter.inbound.api.v1.list_menus_router import list_menus_router
from visit.adapter.inbound.api.v1.list_visit_slots_router import list_visit_slots_router
from visit.adapter.inbound.api.v1.parse_visit_draft_router import parse_visit_draft_router
from visit.adapter.inbound.api.v1.put_visit_record_router import put_visit_record_router
from visit.adapter.inbound.api.v1.register_visit_router import register_visit_router
from visit.adapter.inbound.api.v1.reschedule_visits_router import reschedule_visits_router
from visit.adapter.inbound.api.v1.transition_visits_router import transition_visits_router
from visit.adapter.inbound.api.v1.update_menu_router import update_menu_router
from visit.adapter.inbound.api.v1.update_visit_router import update_visit_router
from visit.adapter.inbound.api.v1.update_visit_settings_router import update_visit_settings_router
from visit.adapter.inbound.api.v1.visit_myself_router import visit_myself_router
from visit.dependencies.hub_ports import get_customer_directory, get_media_library
from visit.dependencies.visit_ledger_provider import get_visit_ledger_use_case


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_engine()
    try:
        yield
    finally:
        await dispose_engine()
        await dispose_redis()


# 고객 검색어·번호 조회가 쿼리 문자열로 오므로 접근 로그에서 가린다(설계 9절 C7).
redact_access_log_queries()

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
app.include_router(list_customers_router)
app.include_router(add_pet_router)
app.include_router(update_pet_router)
app.include_router(mark_pet_passed_away_router)
app.include_router(unmark_pet_passed_away_router)
app.include_router(delete_pet_router)
# visit
app.include_router(get_visit_settings_router)
app.include_router(update_visit_settings_router)
app.include_router(list_closed_dates_router)
app.include_router(add_closed_date_router)
app.include_router(delete_closed_date_router)
app.include_router(list_menus_router)
app.include_router(create_menu_router)
app.include_router(update_menu_router)
app.include_router(archive_menu_router)
# /visits/myself·calendar·slots·defaults 는 /visits/{visit_id} 보다 먼저 붙인다(정수 변환 실패 422 를 피한다).
app.include_router(visit_myself_router)
app.include_router(get_visit_calendar_router)
app.include_router(list_visit_slots_router)
app.include_router(get_visit_defaults_router)
app.include_router(list_day_visits_router)
app.include_router(register_visit_router)
app.include_router(reschedule_visits_router)
app.include_router(transition_visits_router)
app.include_router(parse_visit_draft_router)
app.include_router(get_visit_router)
app.include_router(update_visit_router)
app.include_router(get_next_visit_draft_router)
app.include_router(put_visit_record_router)
# media
app.include_router(media_myself_router)
app.include_router(issue_upload_router)
app.include_router(confirm_upload_router)
install_error_handlers(
    app,
    {
        **AUTH_ERROR_STATUS, **TENANCY_ERROR_STATUS, **PLATFORM_ADMIN_ERROR_STATUS,
        **CUSTOMER_ERROR_STATUS, **VISIT_ERROR_STATUS, **MEDIA_ERROR_STATUS,
    },
)

# 허브 포트 조립 — 스포크끼리는 서로를 모른다. 소비하는 쪽의 "자리"에 구현하는 쪽의 프로바이더를 꽂는다.
app.dependency_overrides[get_shop_access_port] = get_resolve_shop_access_use_case
app.dependency_overrides[get_operator_directory] = get_check_operator_use_case
app.dependency_overrides[get_shop_provisioning] = get_provision_shop_use_case
app.dependency_overrides[get_user_directory] = get_get_user_profiles_use_case
app.dependency_overrides[get_membership_directory] = get_list_memberships_use_case
app.dependency_overrides[get_active_user_guard] = get_guard_active_user_use_case
app.dependency_overrides[get_customer_directory] = get_customer_directory_use_case
app.dependency_overrides[get_visit_ledger] = get_visit_ledger_use_case
app.dependency_overrides[get_media_library] = get_media_library_use_case


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "process": "backend"}
