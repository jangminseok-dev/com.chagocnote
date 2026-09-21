from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from tenancy.domain.errors import InviteExhaustedError, InviteExpiredError, InviteInvalidError
from tenancy.domain.value_objects.role_code import RoleCode


@dataclass(frozen=True)
class Invite:
    id: int
    shop_id: int
    role: RoleCode
    expires_at: datetime
    max_uses: int
    used_count: int
    revoked_at: datetime | None

    def ensure_usable(self, now: datetime) -> None:
        if self.revoked_at is not None:
            raise InviteInvalidError("사용할 수 없는 초대 코드입니다.")
        if now >= self.expires_at:
            raise InviteExpiredError("만료된 초대 코드입니다. 새 코드를 받아 주세요.")
        if self.used_count >= self.max_uses:
            raise InviteExhaustedError("이미 사용된 초대 코드입니다.")
