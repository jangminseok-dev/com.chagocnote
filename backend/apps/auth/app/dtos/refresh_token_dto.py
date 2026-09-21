from dataclasses import dataclass, field


@dataclass(frozen=True)
class RefreshTokenCommand:
    refresh_token: str = field(repr=False)
