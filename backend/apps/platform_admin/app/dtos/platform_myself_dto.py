from dataclasses import dataclass


@dataclass(frozen=True)
class PlatformMyselfQuery:
    id: int
    name: str


@dataclass(frozen=True)
class PlatformMyselfResponse:
    id: int
    name: str
    introduction: str
