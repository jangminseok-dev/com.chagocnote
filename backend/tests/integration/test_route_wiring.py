"""인증 프로세스의 라우트도 같은 구조 검사를 통과해야 한다.

auth_main 은 import 시점에 JWT 개인키를 요구하므로 키를 넣어 주는 wired 픽스처를 먼저 받는다.
"""
import pytest

from tests.route_inspection import find_route_violations

pytestmark = pytest.mark.integration


async def test_인증_프로세스에는_빈_자리도_빠진_가드도_없다(wired):
    import auth_main

    assert find_route_violations(auth_main.app) == []
