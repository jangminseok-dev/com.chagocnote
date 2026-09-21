from dataclasses import dataclass


@dataclass(frozen=True)
class TenancyMyselfQuery:
    id: int
    name: str


@dataclass(frozen=True)
class TenancyMyselfResponse:
    id: int
    name: str
    introduction: str
