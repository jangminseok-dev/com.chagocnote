"""허브 포트 오류 → HTTP 상태 코드.

core 가 허브 포트(ShopAccessPort)를 직접 소비하고, 다른 포트의 오류도 어느 프로세스에서든 같은 상태로
나가야 하므로 맵을 한 곳에 둔다. `install_error_handlers`가 스포크 맵과 함께 자동으로 등록한다.
`tests/test_hub_errors.py`가 HubPortError 의 모든 하위 클래스가 여기 있는지 확인한다.
"""
from __future__ import annotations

from hub.app.errors import (
    FamilyNotFoundError,
    FamilyPetNotFoundError,
    FamilyPetPassedAwayError,
    ShopAccessClosedError,
    ShopAccessDeniedError,
    ShopAccessSuspendedError,
    WithdrawalOwnershipTransferRequiredError,
    WithdrawalShopCloseConfirmRequiredError,
)

HUB_ERROR_STATUS: dict[type[Exception], int] = {
    FamilyNotFoundError: 404,
    FamilyPetNotFoundError: 404,
    FamilyPetPassedAwayError: 422,
    ShopAccessDeniedError: 403,
    ShopAccessClosedError: 403,
    ShopAccessSuspendedError: 403,
    WithdrawalOwnershipTransferRequiredError: 409,
    WithdrawalShopCloseConfirmRequiredError: 409,
}
