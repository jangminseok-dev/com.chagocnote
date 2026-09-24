from dataclasses import dataclass


@dataclass(frozen=True)
class MediaMyselfQuery:
    id: int
    name: str


@dataclass(frozen=True)
class MediaMyselfResponse:
    id: int
    name: str
    introduction: str
