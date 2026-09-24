"""탈퇴가 부르는 오류가 인증 프로세스에서도 HTTP 로 바뀌는지 구조로 고정한다.

auth_main 은 tenancy 의 MembershipLifecyclePort 구현(ApplyWithdrawalInteractor)을 회원 탈퇴 경로에 꽂는다.
그 인터랙터가 막힐 때 던지는 것은 허브 오류(`hub/app/errors.py`)다 — 포트 구현은 자기 도메인 오류를 밖으로
내보내지 않는다(architecture.md). tenancy 맵도 함께 등록하는 것은 설계 B2 가 진입점의 맵 합치기를 유지하라고
해서이며, 방어용이다. 허브 오류 핸들러가 auth 프로세스에 없으면 409 대신 500 이 된다.

"어떤 오류를 던지는가"는 소속 정리 코드가 바뀔 때마다 달라지므로 손으로 적어 두지 않고, 두 맵의 키를 전부 돈다.

auth_main 은 import 시점에 JWT 개인키를 요구하므로, 키를 넣어 주는 wired 픽스처를 먼저 받는다.
"""
import pytest

from core.hub_errors import HUB_ERROR_STATUS
from tenancy.adapter.inbound.api.error_map import TENANCY_ERROR_STATUS

pytestmark = pytest.mark.integration


async def test_모든_허브_오류가_auth_프로세스에도_등록되어_있다(wired):
    import auth_main

    handlers = auth_main.app.exception_handlers
    missing = sorted(e.__name__ for e in HUB_ERROR_STATUS if e not in handlers)
    assert missing == [], f"{missing} 핸들러가 auth_main 에 없다"


async def test_모든_tenancy_오류가_auth_프로세스에도_등록되어_있다(wired):
    import auth_main

    handlers = auth_main.app.exception_handlers
    missing = sorted(e.__name__ for e in TENANCY_ERROR_STATUS if e not in handlers)
    assert missing == [], f"{missing} 핸들러가 auth_main 에 없다"
