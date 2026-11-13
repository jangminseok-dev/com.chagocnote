from dataclasses import dataclass


@dataclass(frozen=True)
class GuardianMyselfQuery:
    id: int
    name: str


@dataclass(frozen=True)
class GuardianMyselfResponse:
    id: int
    name: str
    introduction: str
