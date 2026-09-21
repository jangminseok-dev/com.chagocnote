from dataclasses import dataclass


@dataclass(frozen=True)
class AcceptInviteCommand:
    user_id: int
    code: str


@dataclass(frozen=True)
class AcceptInviteResult:
    shop_id: int
    shop_name: str
    role: str
    member_id: int
