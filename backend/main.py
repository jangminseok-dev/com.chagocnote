"""API 프로세스 — 공개키로 토큰을 검증만 한다. 토큰을 발급할 수 없다."""
import os
import sys
from contextlib import asynccontextmanager

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "apps"))

from fastapi import FastAPI

from core.access_log import redact_access_log_queries
from core.database import dispose_engine, init_engine
from core.observer.in_process_event_bus import get_event_bus, subscribe
from core.redis import dispose_redis
from hub.app.dtos.search_events import SearchSourceChanged
from hub.app.dtos.visit_events import VisitEvent

from auth.adapter.inbound.api.error_map import AUTH_ERROR_STATUS
from auth.adapter.inbound.api.v1.get_me_router import get_me_router
from core.guardian_guard import get_guardian_access_port
from core.http_errors import install_error_handlers
from core.shop_guard import get_shop_access_port
from auth.dependencies.check_operator_provider import get_check_operator_use_case
from auth.dependencies.get_user_profiles_provider import get_get_user_profiles_use_case
from auth.dependencies.guard_active_user_provider import get_guard_active_user_use_case
from auth.dependencies.hub_ports import get_membership_directory
from customer.adapter.inbound.api.error_map import CUSTOMER_ERROR_STATUS
from customer.adapter.inbound.api.v1.add_pet_router import add_pet_router
from customer.adapter.inbound.api.v1.clear_customer_caution_router import clear_customer_caution_router
from customer.adapter.inbound.api.v1.clear_pet_grooming_consent_router import (
    clear_pet_grooming_consent_router,
)
from customer.adapter.inbound.api.v1.customer_myself_router import customer_myself_router
from customer.adapter.inbound.api.v1.delete_customer_router import delete_customer_router
from customer.adapter.inbound.api.v1.delete_pet_router import delete_pet_router
from customer.adapter.inbound.api.v1.get_customer_router import get_customer_router
from customer.adapter.inbound.api.v1.issue_consent_form_router import issue_consent_form_router
from customer.adapter.inbound.api.v1.list_forms_router import list_forms_router
from customer.adapter.inbound.api.v1.revoke_form_router import revoke_form_router
from customer.adapter.inbound.api.v1.get_consent_document_router import get_consent_document_router
from customer.adapter.inbound.api.v1.sign_consent_in_shop_router import sign_consent_in_shop_router
from customer.adapter.inbound.api.v1.list_pet_consent_signatures_router import list_pet_consent_signatures_router
from customer.adapter.inbound.api.v1.get_consent_signature_router import get_consent_signature_router
from customer.adapter.inbound.api.v1.get_consent_signature_image_router import get_consent_signature_image_router
from customer.adapter.inbound.api.v1.get_pet_router import get_pet_router
from customer.adapter.inbound.api.v1.list_customers_router import list_customers_router
from customer.adapter.inbound.api.v1.list_pet_condition_types_router import (
    list_pet_condition_types_router,
)
from customer.adapter.inbound.api.v1.lookup_customer_router import lookup_customer_router
from customer.adapter.inbound.api.v1.mark_pet_passed_away_router import mark_pet_passed_away_router
from customer.adapter.inbound.api.v1.read_public_form_router import read_public_form_router
from customer.adapter.inbound.api.v1.register_customer_router import register_customer_router
from customer.adapter.inbound.api.v1.set_customer_caution_router import set_customer_caution_router
from customer.adapter.inbound.api.v1.submit_public_consent_router import submit_public_consent_router
from customer.adapter.inbound.api.v1.get_form_settings_router import get_form_settings_router
from customer.adapter.inbound.api.v1.update_form_settings_router import update_form_settings_router
from customer.adapter.inbound.api.v1.list_consent_texts_router import list_consent_texts_router
from customer.adapter.inbound.api.v1.update_consent_text_router import update_consent_text_router
from customer.adapter.inbound.api.v1.list_intake_questions_router import list_intake_questions_router
from customer.adapter.inbound.api.v1.issue_intake_form_router import issue_intake_form_router
from customer.adapter.inbound.api.v1.submit_public_intake_router import submit_public_intake_router
from customer.adapter.inbound.api.v1.list_intake_answers_router import list_intake_answers_router
from customer.adapter.inbound.api.v1.get_intake_answer_router import get_intake_answer_router
from customer.adapter.inbound.api.v1.delete_intake_answer_router import delete_intake_answer_router
from customer.dependencies.form_sweeper_provider import start_form_sweeper
from customer.adapter.inbound.api.v1.update_intake_questions_router import update_intake_questions_router
from customer.adapter.inbound.api.v1.set_pet_grooming_consent_router import (
    set_pet_grooming_consent_router,
)
from customer.adapter.inbound.api.v1.unmark_pet_passed_away_router import (
    unmark_pet_passed_away_router,
)
from customer.adapter.inbound.api.v1.update_customer_router import update_customer_router
from customer.adapter.inbound.api.v1.update_pet_router import update_pet_router
from customer.dependencies.customer_directory_provider import get_customer_directory_use_case
from customer.dependencies.customer_search_source_provider import get_customer_search_source_use_case
from customer.dependencies.hub_ports import get_domain_events as get_customer_domain_events
from customer.dependencies.hub_ports import get_guardian_lifecycle as get_customer_guardian_lifecycle
from customer.dependencies.hub_ports import get_media_library as get_customer_media_library
from customer.dependencies.hub_ports import get_search_index as get_customer_search_index
from customer.dependencies.hub_ports import get_shop_profile as get_customer_shop_profile
from customer.dependencies.hub_ports import get_visit_ledger
from media.adapter.inbound.api.error_map import MEDIA_ERROR_STATUS
from media.adapter.inbound.api.v1.confirm_upload_router import confirm_upload_router
from media.adapter.inbound.api.v1.issue_upload_router import issue_upload_router
from media.adapter.inbound.api.v1.media_myself_router import media_myself_router
from media.dependencies.media_library_provider import get_media_library_use_case
from guardian.adapter.inbound.api.error_map import GUARDIAN_ERROR_STATUS
from guardian.adapter.inbound.api.v1.claim_guardian_link_router import claim_guardian_link_router
from guardian.adapter.inbound.api.v1.end_customer_guardian_link_router import end_customer_guardian_link_router
from guardian.adapter.inbound.api.v1.end_guardian_link_router import end_guardian_link_router
from guardian.adapter.inbound.api.v1.get_customer_guardian_link_router import get_customer_guardian_link_router
from guardian.adapter.inbound.api.v1.guardian_myself_router import guardian_myself_router
from guardian.adapter.inbound.api.v1.list_guardian_links_router import list_guardian_links_router
from guardian.dependencies.end_guardian_links_provider import get_end_guardian_links_use_case
from guardian.dependencies.hub_ports import get_active_user_guard as get_guardian_active_user_guard
from guardian.dependencies.hub_ports import get_report_link as get_guardian_report_link
from guardian.dependencies.hub_ports import get_shop_profile as get_guardian_shop_profile
from guardian.dependencies.resolve_guardian_access_provider import get_resolve_guardian_access_use_case
from notification.adapter.inbound.api.error_map import NOTIFICATION_ERROR_STATUS
from notification.adapter.inbound.api.v1.confirm_sender_router import confirm_sender_router
from notification.adapter.inbound.api.v1.get_notification_message_router import get_notification_message_router
from notification.adapter.inbound.api.v1.get_notification_overview_router import get_notification_overview_router
from notification.adapter.inbound.api.v1.link_channel_router import link_channel_router
from notification.adapter.inbound.api.v1.list_visit_notifications_router import list_visit_notifications_router
from notification.adapter.inbound.api.v1.notification_myself_router import notification_myself_router
from notification.adapter.inbound.api.v1.request_channel_token_router import request_channel_token_router
from notification.adapter.inbound.api.v1.request_sender_verification_router import (
    request_sender_verification_router,
)
from notification.adapter.inbound.api.v1.resend_notification_router import resend_notification_router
from notification.adapter.inbound.api.v1.unlink_channel_router import unlink_channel_router
from notification.adapter.inbound.api.v1.update_notification_settings_router import (
    update_notification_settings_router,
)
from notification.adapter.inbound.observer.visit_event_subscriber import handle_visit_event
from notification.app.services.dispatcher_wakeup import wake
from notification.dependencies.dispatcher_ports import DispatcherPorts, configure_dispatcher_ports
from notification.dependencies.dispatcher_provider import start_dispatcher
from notification.dependencies.hub_ports import get_customer_directory as get_notification_customer_directory
from notification.dependencies.hub_ports import get_shop_profile as get_notification_shop_profile
from notification.dependencies.notification_wiring import get_message_gateway
from platform_admin.adapter.inbound.api.error_map import PLATFORM_ADMIN_ERROR_STATUS
from platform_admin.adapter.inbound.api.v1.create_shop_router import create_shop_router
from platform_admin.adapter.inbound.api.v1.platform_myself_router import platform_myself_router
from platform_admin.dependencies.hub_ports import get_operator_directory, get_shop_provisioning
from search.adapter.inbound.api.error_map import SEARCH_ERROR_STATUS
from search.adapter.inbound.api.v1.search_myself_router import search_myself_router
from search.adapter.inbound.api.v1.search_records_router import search_records_router
from search.adapter.inbound.observer.source_changed_subscriber import handle_source_changed
from search.app.services.indexer_wakeup import wake as wake_indexer
from search.dependencies.forget_customer_provider import get_forget_customer_use_case
from search.dependencies.hub_ports import get_customer_directory as get_search_customer_directory
from search.dependencies.hub_ports import get_media_library as get_search_media_library
from search.dependencies.hub_ports import get_visit_ledger as get_search_visit_ledger
from search.dependencies.indexer_ports import IndexerPorts, configure_indexer_ports
from search.dependencies.indexer_provider import start_indexer
from tenancy.adapter.inbound.api.error_map import TENANCY_ERROR_STATUS
from tenancy.adapter.inbound.api.v1.accept_invite_router import accept_invite_router
from tenancy.adapter.inbound.api.v1.change_member_role_router import change_member_role_router
from tenancy.adapter.inbound.api.v1.create_invite_router import create_invite_router
from tenancy.adapter.inbound.api.v1.get_shop_router import get_shop_router
from tenancy.adapter.inbound.api.v1.list_members_router import list_members_router
from tenancy.adapter.inbound.api.v1.remove_member_router import remove_member_router
from tenancy.adapter.inbound.api.v1.tenancy_myself_router import tenancy_myself_router
from tenancy.adapter.inbound.api.v1.update_shop_router import update_shop_router
from tenancy.dependencies.get_shop_profile_provider import get_shop_profile_use_case
from tenancy.dependencies.hub_ports import get_active_user_guard, get_user_directory
from tenancy.dependencies.list_memberships_provider import get_list_memberships_use_case
from tenancy.dependencies.provision_shop_provider import get_provision_shop_use_case
from tenancy.dependencies.resolve_shop_access_provider import get_resolve_shop_access_use_case
from visit.adapter.inbound.api.error_map import VISIT_ERROR_STATUS
from visit.adapter.inbound.api.v1.add_closed_date_router import add_closed_date_router
from visit.adapter.inbound.api.v1.append_record_media_router import append_record_media_router
from visit.adapter.inbound.api.v1.archive_menu_router import archive_menu_router
from visit.adapter.inbound.api.v1.create_menu_router import create_menu_router
from visit.adapter.inbound.api.v1.delete_closed_date_router import delete_closed_date_router
from visit.adapter.inbound.api.v1.delete_visit_record_router import delete_visit_record_router
from visit.adapter.inbound.api.v1.get_next_visit_draft_router import get_next_visit_draft_router
from visit.adapter.inbound.api.v1.get_report_settings_router import get_report_settings_router
from visit.adapter.inbound.api.v1.get_sales_goal_router import get_sales_goal_router
from visit.adapter.inbound.api.v1.get_sales_summary_router import get_sales_summary_router
from visit.adapter.inbound.api.v1.get_visit_calendar_router import get_visit_calendar_router
from visit.adapter.inbound.api.v1.get_visit_checks_router import get_visit_checks_router
from visit.adapter.inbound.api.v1.get_visit_defaults_router import get_visit_defaults_router
from visit.adapter.inbound.api.v1.get_visit_report_router import get_visit_report_router
from visit.adapter.inbound.api.v1.get_visit_router import get_visit_router
from visit.adapter.inbound.api.v1.get_visit_settings_router import get_visit_settings_router
from visit.adapter.inbound.api.v1.list_closed_dates_router import list_closed_dates_router
from visit.adapter.inbound.api.v1.list_day_visits_router import list_day_visits_router
from visit.adapter.inbound.api.v1.list_due_pets_router import list_due_pets_router
from visit.adapter.inbound.api.v1.list_menus_router import list_menus_router
from visit.adapter.inbound.api.v1.list_sales_visits_router import list_sales_visits_router
from visit.adapter.inbound.api.v1.list_visit_feed_router import list_visit_feed_router
from visit.adapter.inbound.api.v1.list_visit_slots_router import list_visit_slots_router
from visit.adapter.inbound.api.v1.mark_report_viewed_router import mark_report_viewed_router
from visit.adapter.inbound.api.v1.parse_visit_draft_router import parse_visit_draft_router
from visit.adapter.inbound.api.v1.put_visit_record_router import put_visit_record_router
from visit.adapter.inbound.api.v1.read_public_report_router import read_public_report_router
from visit.adapter.inbound.api.v1.register_visit_router import register_visit_router
from visit.adapter.inbound.api.v1.reschedule_visits_router import reschedule_visits_router
from visit.adapter.inbound.api.v1.revoke_visit_report_router import revoke_visit_report_router
from visit.adapter.inbound.api.v1.send_visit_report_router import send_visit_report_router
from visit.adapter.inbound.api.v1.transition_visits_router import transition_visits_router
from visit.adapter.inbound.api.v1.update_menu_router import update_menu_router
from visit.adapter.inbound.api.v1.update_report_settings_router import update_report_settings_router
from visit.adapter.inbound.api.v1.update_sales_goal_router import update_sales_goal_router
from visit.adapter.inbound.api.v1.update_visit_router import update_visit_router
from visit.adapter.inbound.api.v1.update_visit_settings_router import update_visit_settings_router
from visit.adapter.inbound.api.v1.visit_myself_router import visit_myself_router
from visit.dependencies.hub_ports import get_customer_directory, get_domain_events
from visit.dependencies.hub_ports import get_media_library as get_visit_media_library
from visit.dependencies.hub_ports import get_shop_profile
from visit.dependencies.hub_ports import get_guardian_forms
from visit.adapter.inbound.api.v1.build_send_bundle_router import build_send_bundle_router
from customer.dependencies.guardian_form_provider import get_guardian_form_use_case
from visit.dependencies.visit_ledger_provider import get_visit_ledger_use_case
from visit.dependencies.visit_search_source_provider import get_visit_search_source_use_case
from visit.adapter.inbound.api.v1.guardian_reports_router import (
    list_guardian_pets_router,
    list_guardian_reports_router,
    read_guardian_report_router,
)
from visit.dependencies.resolve_report_link_provider import get_resolve_report_link_use_case


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_engine()
    # 발송 게이트웨이를 기동 때 만든다 — 운영에서 솔라피 키가 비면 첫 발송이 아니라 여기서 멈춘다(설계 6.1).
    get_message_gateway()
    # 디스패처 — 프로세스에 asyncio 작업 하나(설계 3.2). 끝낼 때 정지를 알리고 깨워서 기다림을 끊는다.
    task, stop = start_dispatcher()
    # 검색 색인기 — 같은 모양의 작업 하나(⑨ 설계 3.4). 임베딩 프로세스가 죽어 있어도 기동한다.
    indexer_task, indexer_stop = start_indexer()
    # 서류 청소 — 보관 기간이 지난 문진표의 답을 하루 한 번 지운다(⑪ 설계 3.4).
    sweeper_task, sweeper_stop = start_form_sweeper()
    try:
        yield
    finally:
        stop.set()
        indexer_stop.set()
        sweeper_stop.set()
        wake()
        wake_indexer()
        await task
        await indexer_task
        await sweeper_task
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
app.include_router(set_customer_caution_router)
app.include_router(clear_customer_caution_router)
app.include_router(set_pet_grooming_consent_router)
app.include_router(clear_pet_grooming_consent_router)
app.include_router(add_pet_router)
app.include_router(update_pet_router)
# 서류(⑪) — 동의서 보내기·끊기·현장 서명·서명 보기
app.include_router(issue_consent_form_router)
app.include_router(list_forms_router)
app.include_router(revoke_form_router)
app.include_router(get_consent_document_router)
app.include_router(sign_consent_in_shop_router)
app.include_router(list_pet_consent_signatures_router)
app.include_router(get_consent_signature_router)
app.include_router(get_consent_signature_image_router)
app.include_router(read_public_form_router)
app.include_router(submit_public_consent_router)
app.include_router(get_form_settings_router)
app.include_router(update_form_settings_router)
app.include_router(list_consent_texts_router)
app.include_router(update_consent_text_router)
app.include_router(list_intake_questions_router)
app.include_router(issue_intake_form_router)
app.include_router(submit_public_intake_router)
app.include_router(list_intake_answers_router)
app.include_router(get_intake_answer_router)
app.include_router(delete_intake_answer_router)
app.include_router(update_intake_questions_router)
app.include_router(build_send_bundle_router)
app.include_router(mark_pet_passed_away_router)
app.include_router(unmark_pet_passed_away_router)
app.include_router(delete_pet_router)
# visit
app.include_router(get_visit_settings_router)
app.include_router(update_visit_settings_router)
app.include_router(get_report_settings_router)
app.include_router(update_report_settings_router)
# ⑧ 매출 — 모두 sales:read(사장만)
app.include_router(get_sales_summary_router)
app.include_router(list_sales_visits_router)
app.include_router(list_due_pets_router)
app.include_router(get_sales_goal_router)
app.include_router(update_sales_goal_router)
app.include_router(list_closed_dates_router)
app.include_router(add_closed_date_router)
app.include_router(delete_closed_date_router)
app.include_router(list_menus_router)
app.include_router(create_menu_router)
app.include_router(update_menu_router)
app.include_router(archive_menu_router)
# /visits/myself·calendar·slots·defaults·feed 는 /visits/{visit_id} 보다 먼저 붙인다(정수 변환 실패 422 를 피한다).
app.include_router(visit_myself_router)
app.include_router(get_visit_calendar_router)
app.include_router(list_visit_feed_router)
app.include_router(list_visit_slots_router)
app.include_router(get_visit_defaults_router)
app.include_router(get_visit_checks_router)
app.include_router(list_day_visits_router)
app.include_router(register_visit_router)
app.include_router(reschedule_visits_router)
app.include_router(transition_visits_router)
app.include_router(parse_visit_draft_router)
app.include_router(get_visit_router)
app.include_router(update_visit_router)
app.include_router(get_next_visit_draft_router)
app.include_router(put_visit_record_router)
app.include_router(append_record_media_router)
app.include_router(delete_visit_record_router)
app.include_router(get_visit_report_router)
app.include_router(send_visit_report_router)
app.include_router(revoke_visit_report_router)
# 로그인 없이 열리는 경로 — 더할 때는 tests/route_inspection.py 의 허용 목록에도 적는다.
app.include_router(read_public_report_router)
app.include_router(mark_report_viewed_router)
# notification
app.include_router(notification_myself_router)
app.include_router(get_notification_overview_router)
app.include_router(request_channel_token_router)
app.include_router(link_channel_router)
app.include_router(unlink_channel_router)
app.include_router(update_notification_settings_router)
app.include_router(request_sender_verification_router)
app.include_router(confirm_sender_router)
# /visits/{visit_id}/notifications 는 visit 의 /visits/{visit_id} 경로들과 겹치지 않는다(뒤에 붙여도 된다).
app.include_router(list_visit_notifications_router)
app.include_router(resend_notification_router)
app.include_router(get_notification_message_router)
# media
app.include_router(guardian_myself_router)
app.include_router(claim_guardian_link_router)
app.include_router(list_guardian_links_router)
app.include_router(end_guardian_link_router)
app.include_router(get_customer_guardian_link_router)
app.include_router(end_customer_guardian_link_router)
# 보호자용 읽기는 visit 이 소유한다(알림장은 visit 의 것이다) — 보호자 가드를 거친다.
app.include_router(list_guardian_pets_router)
app.include_router(list_guardian_reports_router)
app.include_router(read_guardian_report_router)

app.include_router(media_myself_router)
app.include_router(issue_upload_router)
app.include_router(confirm_upload_router)
# search — 기록 검색(⑨). /search/myself 와 /search 는 겹치지 않는다.
app.include_router(search_myself_router)
app.include_router(search_records_router)
install_error_handlers(
    app,
    {
        **AUTH_ERROR_STATUS, **TENANCY_ERROR_STATUS, **PLATFORM_ADMIN_ERROR_STATUS,
        **CUSTOMER_ERROR_STATUS, **VISIT_ERROR_STATUS, **MEDIA_ERROR_STATUS, **NOTIFICATION_ERROR_STATUS,
        **GUARDIAN_ERROR_STATUS, **SEARCH_ERROR_STATUS,
    },
)

# 허브 포트 조립 — 스포크끼리는 서로를 모른다. 소비하는 쪽의 "자리"에 구현하는 쪽의 프로바이더를 꽂는다.
app.dependency_overrides[get_shop_access_port] = get_resolve_shop_access_use_case
app.dependency_overrides[get_operator_directory] = get_check_operator_use_case
app.dependency_overrides[get_shop_provisioning] = get_provision_shop_use_case
app.dependency_overrides[get_user_directory] = get_get_user_profiles_use_case
app.dependency_overrides[get_membership_directory] = get_list_memberships_use_case
app.dependency_overrides[get_active_user_guard] = get_guard_active_user_use_case
# guardian: 잇기가 유저 행을 잠그고(auth), 알림장 토큰을 매장·고객으로 푼다(visit).
app.dependency_overrides[get_guardian_active_user_guard] = get_guard_active_user_use_case
app.dependency_overrides[get_guardian_report_link] = get_resolve_report_link_use_case
app.dependency_overrides[get_guardian_shop_profile] = get_shop_profile_use_case
# 보호자 가드(core/guardian_guard)의 접근 확인은 guardian 이 구현한다.
app.dependency_overrides[get_guardian_access_port] = get_resolve_guardian_access_use_case
# 고객 익명화가 보호자 연결을 끝낸다.
app.dependency_overrides[get_customer_guardian_lifecycle] = get_end_guardian_links_use_case
app.dependency_overrides[get_customer_directory] = get_customer_directory_use_case
app.dependency_overrides[get_guardian_forms] = get_guardian_form_use_case
app.dependency_overrides[get_visit_ledger] = get_visit_ledger_use_case
app.dependency_overrides[get_visit_media_library] = get_media_library_use_case
app.dependency_overrides[get_customer_media_library] = get_media_library_use_case
app.dependency_overrides[get_shop_profile] = get_shop_profile_use_case
app.dependency_overrides[get_customer_shop_profile] = get_shop_profile_use_case
app.dependency_overrides[get_notification_shop_profile] = get_shop_profile_use_case
app.dependency_overrides[get_notification_customer_directory] = get_customer_directory_use_case
# search: 결과 줄의 이름(customer)과 프로필 사진(visit 의 대표 → media 의 주소).
app.dependency_overrides[get_search_customer_directory] = get_customer_directory_use_case
app.dependency_overrides[get_search_visit_ledger] = get_visit_ledger_use_case
app.dependency_overrides[get_search_media_library] = get_media_library_use_case
# 도메인 이벤트 — visit 이 발행하고 core 의 같은 세션 동기 버스가 구독자에 넘긴다. 구독자는 여기서 꽂는다.
app.dependency_overrides[get_domain_events] = get_event_bus
# customer 도 발행한다(검색되는 글이 바뀌었다). 고객 익명화는 검색 문서를 그 트랜잭션에서 곧바로 지운다.
app.dependency_overrides[get_customer_domain_events] = get_event_bus
app.dependency_overrides[get_customer_search_index] = get_forget_customer_use_case
subscribe(handle_visit_event, VisitEvent)
# 검색 — 글이 바뀐 대상을 다시 색인할 줄에 넣는다(같은 트랜잭션). 글은 요청 밖의 색인기가 읽는다.
subscribe(handle_source_changed, SearchSourceChanged)
# 디스패처는 요청 밖이라 Depends 자리를 못 쓴다 — 같은 세 프로바이더를 세션을 받는 공장으로 꽂는다.
configure_dispatcher_ports(DispatcherPorts(
    shop_profile=get_shop_profile_use_case, customer_directory=get_customer_directory_use_case,
    visit_ledger=get_visit_ledger_use_case,
))
# 검색 색인기도 요청 밖이다 — 글은 visit·customer 가 구현한 SearchSourcePort 로 읽는다.
configure_indexer_ports(IndexerPorts(
    shop_profile=get_shop_profile_use_case, customer_directory=get_customer_directory_use_case,
    visit_source=get_visit_search_source_use_case, customer_source=get_customer_search_source_use_case,
))


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "process": "backend"}
