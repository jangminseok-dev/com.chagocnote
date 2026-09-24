"""라우트의 의존성 트리를 훑어 조립·가드 실수를 찾는다. 두 프로세스의 테스트가 함께 쓴다.

손으로 관리하는 목록을 두지 않으려는 것이다. 자리를 새로 만들고 채우는 것을 잊으면
목록 없이도 여기서 걸린다. 자리는 override 되어도 트리에는 원래 함수로 남으므로,
그 함수가 app.dependency_overrides 의 키인지만 본다. 꽂힌 프로바이더의 하위 의존성은 보지 않는다.
"""
from __future__ import annotations

from typing import Any, Iterator

from fastapi import FastAPI
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute, iter_route_contexts

from auth.dependencies.recent_login_guard import require_recent_login
from core.shop_guard import get_shop_access_port, get_shop_context
from platform_admin.dependencies.operator_guard import require_operator

# 계정을 빼앗는 데 쓰일 수 있는 경로. 새로 더하는 민감 경로도 여기에 적는다.
_RECENT_LOGIN_PREFIXES = ("/v1/auth/identities", "/v1/auth/account")


def _is_slot(call: Any) -> bool:
    """허브 포트 "자리" — 스포크의 dependencies/hub_ports 함수와 매장 접근 확인 자리."""
    return call is get_shop_access_port or getattr(call, "__module__", "").endswith(
        ".dependencies.hub_ports"
    )


def _calls(dependant: Dependant) -> Iterator[Any]:
    for sub in dependant.dependencies:
        yield sub.call
        yield from _calls(sub)


def routes_calling(app: FastAPI, dependency: Any) -> set[str]:
    """dependency 를 의존성 트리 어딘가에서 거치는 경로를 "METHOD path" 로 돌려준다."""
    found = set()
    for ctx in iter_route_contexts(app.routes):
        if isinstance(ctx.original_route, APIRoute) and dependency in set(_calls(ctx.dependant)):
            found.update(f"{method} {ctx.path}" for method in ctx.original_route.methods)
    return found


def find_route_violations(app: FastAPI) -> list[str]:
    """위반을 사람이 읽을 수 있는 줄로 돌려준다. 빈 목록이면 문제가 없다."""
    violations = []
    for ctx in iter_route_contexts(app.routes):
        if not isinstance(ctx.original_route, APIRoute):
            continue
        path, calls = ctx.path, set(_calls(ctx.dependant))
        for call in calls:
            if _is_slot(call) and call not in app.dependency_overrides:
                violations.append(f"{path}: 허브 포트 자리 {call.__name__} 가 비어 있다")
        if "{shop_id}" in path and get_shop_context not in calls:
            violations.append(f"{path}: 매장 범위 경로인데 get_shop_context 를 거치지 않는다")
        if path.startswith("/v1/platform/") and require_operator not in calls:
            violations.append(f"{path}: 운영자 표면인데 require_operator 를 거치지 않는다")
        if path.startswith(_RECENT_LOGIN_PREFIXES) and require_recent_login not in calls:
            violations.append(f"{path}: 민감한 계정 경로인데 require_recent_login 을 거치지 않는다")
    return sorted(violations)
