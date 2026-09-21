from dataclasses import dataclass


@dataclass(frozen=True)
class CreateShopCommand:
    name: str
    business_type: str
