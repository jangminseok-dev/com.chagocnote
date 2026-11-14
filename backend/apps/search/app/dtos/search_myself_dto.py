from dataclasses import dataclass


@dataclass(frozen=True)
class SearchMyselfQuery:
    id: int
    name: str


@dataclass(frozen=True)
class SearchMyselfResponse:
    id: int
    name: str
    introduction: str
