from dataclasses import dataclass


@dataclass(frozen=True)
class AuthMyselfQuery:
    id: int
    name: str


@dataclass(frozen=True)
class AuthMyselfResponse:
    id: int
    name: str
    introduction: str
