from dataclasses import dataclass


@dataclass(frozen=True)
class GrantOperatorCommand:
    user_id: int
