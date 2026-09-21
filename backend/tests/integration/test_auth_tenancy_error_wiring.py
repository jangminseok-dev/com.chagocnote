"""탈퇴가 부르는 tenancy 오류가 인증 프로세스에서도 HTTP 로 바뀌는지 구조로 고정한다.

auth_main 은 tenancy 의 MembershipLifecyclePort 구현(ApplyWithdrawalInteractor)을 회원 탈퇴 경로에
꽂는다. 그 인터랙터가 던질 수 있는 tenancy 오류의 핸들러가 auth 프로세스에 없으면, "다른 사장을 먼저
지정하세요"가 409 대신 처리되지 않은 예외로 500 이 된다.

"어떤 오류를 던지는가"는 소속 정리 코드가 바뀔 때마다 달라지므로, 두 가지를 손으로 적어 두지 않고
`TENANCY_ERROR_STATUS`의 키를 전부 돈다. tenancy 오류가 새로 생기면 이 테스트가 함께 따라온다.

auth_main 은 import 시점에 JWT 개인키를 요구하므로, 키를 넣어 주는 wired 픽스처를 먼저 받는다.
"""
import pytest

from tenancy.adapter.inbound.api.error_map import TENANCY_ERROR_STATUS

pytestmark = pytest.mark.integration


async def test_모든_tenancy_오류가_auth_프로세스에도_등록되어_있다(wired):
    import auth_main

    handlers = auth_main.app.exception_handlers
    missing = sorted(e.__name__ for e in TENANCY_ERROR_STATUS if e not in handlers)
    assert missing == [], f"{missing} 핸들러가 auth_main 에 없다"
