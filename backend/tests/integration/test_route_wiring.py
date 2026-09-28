"""인증 프로세스의 라우트도 같은 구조 검사를 통과해야 한다.

auth_main 은 import 시점에 JWT 개인키를 요구하므로 키를 넣어 주는 wired 픽스처를 먼저 받는다.
"""
import pytest

from auth.dependencies.recent_login_guard import require_recent_login
from tests.route_inspection import find_route_violations, routes_calling, routes_without_login

pytestmark = pytest.mark.integration


async def test_인증_프로세스에는_빈_자리도_빠진_가드도_없다(wired):
    import auth_main

    assert find_route_violations(auth_main.app) == []


async def test_연결_해제_탈퇴는_실제로_최근_로그인_가드를_거친다(wired):
    """접두어 규칙은 경로 이름이 바뀌면 아무것도 검사하지 않고 조용히 통과한다. 그래서 대상을 직접 못 박는다."""
    import auth_main

    assert routes_calling(auth_main.app, require_recent_login) >= {
        "POST /v1/auth/identities",
        "DELETE /v1/auth/identities/{provider}",
        "DELETE /v1/auth/account",
    }


async def test_인증_프로세스에서_로그인_없이_열리는_경로는_다섯뿐이다(wired):
    """로그인 자체와 토큰 갱신·로그아웃(리프레시 토큰으로 확인한다), 상태 확인, 자기소개. 공개 경로는 없다."""
    import auth_main

    assert routes_without_login(auth_main.app) == {
        "GET /v1/auth/health",
        "GET /v1/auth/myself",
        "POST /v1/auth/social",
        "POST /v1/auth/refresh",
        "POST /v1/auth/logout",
    }
