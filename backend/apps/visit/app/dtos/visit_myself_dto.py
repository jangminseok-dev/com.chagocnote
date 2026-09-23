from dataclasses import dataclass


@dataclass(frozen=True)
class VisitMyselfQuery:
    id: int
    name: str


@dataclass(frozen=True)
class VisitMyselfResponse:
    id: int
    name: str
    introduction: str
