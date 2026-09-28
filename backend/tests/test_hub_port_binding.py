"""API 프로세스의 라우트를 훑어 조립·가드 실수를 잡는다. 손으로 관리하는 목록은 두지 않는다."""
import pytest
from fastapi import Depends, FastAPI

import main
from core.shop_guard import get_shop_access_port
from tenancy.dependencies.hub_ports import get_user_directory
from tenancy.dependencies.get_shop_profile_provider import get_shop_profile_use_case
from tests.route_inspection import find_route_violations
from visit.dependencies.hub_ports import get_shop_profile


def test_API_프로세스에는_빈_자리도_빠진_가드도_없다():
    assert find_route_violations(main.app) == []


def test_매장_공개_정보_자리는_tenancy_의_구현으로_채운다():
    """쓰는 라우트가 아직 없어 위의 검사에는 걸리지 않는다."""
    assert main.app.dependency_overrides[get_shop_profile] is get_shop_profile_use_case
    with pytest.raises(RuntimeError):
        get_shop_profile()


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
