"""탈퇴가 부르는 tenancy 오류가 인증 프로세스에서도 HTTP 로 바뀌는지 구조로 고정한다.

auth_main 은 tenancy 의 MembershipLifecyclePort 구현(ApplyWithdrawalInteractor)을 회원 탈퇴 경로에
꽂는다. 그 인터랙터가 던질 수 있는 tenancy 오류(OwnershipTransferRequiredError·
ShopCloseConfirmRequiredError)의 핸들러가 auth 프로세스에 없으면, "다른 사장을 먼저 지정하세요"가
409 대신 처리되지 않은 예외로 500 이 된다.

auth_main 은 import 시점에 JWT 개인키를 요구하므로, 키를 넣어 주는 wired 픽스처를 먼저 받는다.
"""
import pytest

from tenancy.domain.errors import OwnershipTransferRequiredError, ShopCloseConfirmRequiredError

pytestmark = pytest.mark.integration

# ApplyWithdrawalInteractor.apply_withdrawal 이 실제로 던지는 tenancy 오류 전부.
# (리포지토리 호출들은 도메인 오류를 던지지 않으므로, 이 두 개가 전부다.)
_RAISED_BY_APPLY_WITHDRAWAL = (OwnershipTransferRequiredError, ShopCloseConfirmRequiredError)


async def test_탈퇴가_부르는_tenancy_오류가_auth_프로세스에도_등록되어_있다(wired):
    import auth_main

    handlers = auth_main.app.exception_handlers
    for exc_type in _RAISED_BY_APPLY_WITHDRAWAL:
        assert exc_type in handlers, f"{exc_type.__name__} 핸들러가 auth_main 에 없다"
