from dataclasses import dataclass


@dataclass(frozen=True)
class PlatformMyselfQuery:
    id: int
    name: str
    user_id: int


@dataclass(frozen=True)
class PlatformMyselfResponse:
    id: int
    name: str
    introduction: str
