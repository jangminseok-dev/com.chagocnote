from dataclasses import dataclass


@dataclass(frozen=True)
class CustomerMyselfQuery:
    id: int
    name: str


@dataclass(frozen=True)
class CustomerMyselfResponse:
    id: int
    name: str
    introduction: str
