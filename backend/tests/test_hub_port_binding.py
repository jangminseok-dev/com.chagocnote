"""API 프로세스의 라우트를 훑어 조립·가드 실수를 잡는다. 손으로 관리하는 목록은 두지 않는다."""
import pytest
from fastapi import Depends, FastAPI

import main
from core.observer.in_process_event_bus import get_event_bus, subscribers
from core.shop_guard import get_shop_access_port
from customer.dependencies.customer_directory_provider import get_customer_directory_use_case
from notification.adapter.inbound.observer.visit_event_subscriber import handle_visit_event
from notification.dependencies.dispatcher_ports import dispatcher_ports
from notification.dependencies.hub_ports import get_customer_directory as get_notification_customer_directory
from notification.dependencies.hub_ports import get_shop_profile as get_notification_shop_profile
from tenancy.dependencies.hub_ports import get_user_directory
from tenancy.dependencies.get_shop_profile_provider import get_shop_profile_use_case
from core.security import get_current_user_id
from core.shop_guard import get_shop_context
from tests.route_inspection import find_route_violations, routes_without_login
from visit.dependencies.hub_ports import get_domain_events, get_shop_profile
from visit.dependencies.visit_ledger_provider import get_visit_ledger_use_case


def test_API_프로세스에는_빈_자리도_빠진_가드도_없다():
    assert find_route_violations(main.app) == []


def test_API_프로세스에서_로그인_없이_열리는_경로는_넷뿐이다():
    """여기에 경로를 더하는 것은 로그인 없는 표면을 넓히는 일이다 — 공개 경로면 route_inspection 의 허용 목록에도 적는다."""
    assert routes_without_login(main.app) == {
        "GET /health",
        "GET /v1/shops/myself",
        "GET /v1/public/report",
        "POST /v1/public/report/viewed",
    }


def test_매장_공개_정보_자리는_tenancy_의_구현으로_채운다():
    assert main.app.dependency_overrides[get_shop_profile] is get_shop_profile_use_case
    with pytest.raises(RuntimeError):
        get_shop_profile()


def test_도메인_이벤트_자리는_core_의_버스로_채운다():
    assert main.app.dependency_overrides[get_domain_events] is get_event_bus
    with pytest.raises(RuntimeError):
        get_domain_events()


def test_notification_구독자가_버스에_등록되어_있다():
    assert handle_visit_event in subscribers()


def test_notification_의_매장_공개_정보와_고객_연락처_자리는_tenancy_customer_의_구현으로_채운다():
    """share_text 가 매장 이름·보호자 이름을 읽는 요청 안의 자리 — 디스패처의 공장과 같은 프로바이더다."""
    assert main.app.dependency_overrides[get_notification_shop_profile] is get_shop_profile_use_case
    assert main.app.dependency_overrides[get_notification_customer_directory] is get_customer_directory_use_case
    for slot in (get_notification_shop_profile, get_notification_customer_directory):
        with pytest.raises(RuntimeError):
            slot()


def test_디스패처의_허브_포트_공장은_tenancy_customer_visit_의_프로바이더다():
    ports = dispatcher_ports()
    assert ports.shop_profile is get_shop_profile_use_case
    assert ports.customer_directory is get_customer_directory_use_case
    assert ports.visit_ledger is get_visit_ledger_use_case


def _app_with(path, dependency=None):
    app = FastAPI()
    deps = [Depends(dependency)] if dependency else []

    @app.get(path, dependencies=deps)
    async def route() -> dict:
        return {}

    return app


def test_채우지_않은_허브_포트_자리를_잡는다():
    violations = find_route_violations(_app_with("/v1/thing", get_user_directory))
    assert violations == ["/v1/thing: 허브 포트 자리 get_user_directory 가 비어 있다"]


def test_채운_자리는_잡지_않는다():
    app = _app_with("/v1/thing", get_user_directory)
    app.dependency_overrides[get_user_directory] = lambda: None
    assert find_route_violations(app) == []


def test_매장_접근_확인_자리도_잡는다():
    violations = find_route_violations(_app_with("/v1/thing", get_shop_access_port))
    assert violations == ["/v1/thing: 허브 포트 자리 get_shop_access_port 가 비어 있다"]


def test_get_shop_context_를_거치지_않는_매장_범위_경로를_잡는다():
    violations = find_route_violations(_app_with("/v1/shops/{shop_id}/thing"))
    assert violations == ["/v1/shops/{shop_id}/thing: 매장 범위 경로인데 get_shop_context 를 거치지 않는다"]


def test_require_operator_를_거치지_않는_운영자_경로를_잡는다():
    violations = find_route_violations(_app_with("/v1/platform/thing"))
    assert violations == ["/v1/platform/thing: 운영자 표면인데 require_operator 를 거치지 않는다"]


def test_허용_목록에_없는_공개_경로를_잡는다():
    violations = find_route_violations(_app_with("/v1/public/thing"))
    assert violations == ["/v1/public/thing: 공개 경로인데 허용 목록에 없다"]


def test_허용_목록의_경로라도_메서드가_다르면_잡는다():
    app = FastAPI()

    @app.post("/v1/public/report")
    async def route() -> dict:
        return {}

    assert find_route_violations(app) == ["/v1/public/report: 공개 경로인데 허용 목록에 없다"]


@pytest.mark.parametrize("dependency", [get_current_user_id, get_shop_context])
def test_로그인이나_매장_확인을_거치는_공개_경로를_잡는다(dependency):
    app = _app_with("/v1/public/report", dependency)
    app.dependency_overrides[get_shop_access_port] = lambda: None
    assert find_route_violations(app) == ["/v1/public/report: 공개 경로인데 로그인이나 매장 확인을 거친다"]


def test_로그인_없이_열리는_경로를_센다():
    app = _app_with("/v1/thing", get_current_user_id)

    @app.post("/v1/open")
    async def route() -> dict:
        return {}

    assert routes_without_login(app) == {"POST /v1/open"}


def test_guardian_의_자리와_보호자_가드는_visit_auth_tenancy_guardian_의_구현으로_채운다():
    from auth.dependencies.guard_active_user_provider import get_guard_active_user_use_case
    from core.guardian_guard import get_guardian_access_port
    from guardian.dependencies.hub_ports import get_active_user_guard as get_guardian_active_user_guard
    from guardian.dependencies.hub_ports import get_report_link as get_guardian_report_link
    from guardian.dependencies.hub_ports import get_shop_profile as get_guardian_shop_profile
    from guardian.dependencies.resolve_guardian_access_provider import get_resolve_guardian_access_use_case
    from visit.dependencies.resolve_report_link_provider import get_resolve_report_link_use_case

    overrides = main.app.dependency_overrides
    assert overrides[get_guardian_report_link] is get_resolve_report_link_use_case
    assert overrides[get_guardian_active_user_guard] is get_guard_active_user_use_case
    assert overrides[get_guardian_shop_profile] is get_shop_profile_use_case
    assert overrides[get_guardian_access_port] is get_resolve_guardian_access_use_case


def test_탈퇴와_고객_익명화의_보호자_연결_끝내기_자리는_guardian_의_구현으로_채운다():
    import auth_main
    from auth.dependencies.hub_ports import get_guardian_lifecycle as auth_slot
    from customer.dependencies.hub_ports import get_guardian_lifecycle as customer_slot
    from guardian.dependencies.end_guardian_links_provider import get_end_guardian_links_use_case

    assert auth_main.app.dependency_overrides[auth_slot] is get_end_guardian_links_use_case
    assert main.app.dependency_overrides[customer_slot] is get_end_guardian_links_use_case
