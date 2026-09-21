from dataclasses import dataclass, field


@dataclass(frozen=True)
class LogoutCommand:
    refresh_token: str = field(repr=False)
