"""허브 포트가 던지는 오류 — 스포크 경계를 넘는 예외의 계약.

포트를 구현하는 스포크는 자기 도메인 오류를 밖으로 내보내지 않고 여기 있는 예외로 바꿔 던진다.
소비하는 스포크와 core 는 이 타입만 알면 된다(리스코프: 구현이 무엇을 던지는지 계약이 말한다).
HTTP 상태는 `core/hub_errors.py`가 정하고, 두 진입점의 오류 처리기에 자동으로 들어간다.
code 는 응답 본문의 code 로 나간다 — 구현 스포크가 자기 라우터에서 쓰는 코드와 같게 둔다.
"""
from __future__ import annotations


class HubPortError(Exception):
    """허브 포트 오류의 바탕. 새 포트가 오류를 던지게 되면 여기서 파생하고 `core/hub_errors.py`에 상태를 적는다."""

    code = "HUB_PORT_ERROR"


# --- CustomerDirectoryPort.lock_family (구현: customer) -----------------------------------------

class FamilyNotFoundError(HubPortError):
    """살아 있는 이 매장의 고객이 아니다(익명화됐거나 다른 매장)."""

    code = "CUSTOMER_NOT_FOUND"


class FamilyPetNotFoundError(HubPortError):
    """그 보호자의 아이가 아니다(다른 가족·다른 매장·지워진 아이)."""

    code = "PET_NOT_FOUND"


class FamilyPetPassedAwayError(HubPortError):
    """무지개다리를 건넌 아이다 — 새로 시간을 차지하는 예약을 잡을 수 없다."""

    code = "PET_PASSED_AWAY"


# --- ShopAccessPort.resolve (구현: tenancy, 소비: core/shop_guard) --------------------------------

class ShopAccessDeniedError(HubPortError):
    """이 매장의 멤버가 아니다. 매장이 없는 경우와 구분해 주지 않는다(매장 존재 여부를 흘리지 않는다)."""

    code = "NOT_A_MEMBER"


class ShopAccessClosedError(HubPortError):
    code = "SHOP_CLOSED"


class ShopAccessSuspendedError(HubPortError):
    code = "SHOP_SUSPENDED"


# --- MembershipLifecyclePort.apply_withdrawal (구현: tenancy, 소비: auth 탈퇴) ---------------------

class WithdrawalOwnershipTransferRequiredError(HubPortError):
    """탈퇴하려는 유저가 유일한 사장인데 다른 멤버가 남아 있다 — 사장을 먼저 넘겨야 한다."""

    code = "OWNERSHIP_TRANSFER_REQUIRED"


class WithdrawalShopCloseConfirmRequiredError(HubPortError):
    """탈퇴하면 혼자 운영하던 매장이 닫힌다 — 확인을 받아야 한다."""

    code = "SHOP_CLOSE_CONFIRM_REQUIRED"
