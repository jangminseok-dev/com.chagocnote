from dataclasses import dataclass


@dataclass(frozen=True)
class CreateShopCommand:
    user_id: int
    name: str
    business_type: str
