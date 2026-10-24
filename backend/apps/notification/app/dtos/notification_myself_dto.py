from dataclasses import dataclass


@dataclass(frozen=True)
class NotificationMyselfQuery:
    id: int
    name: str


@dataclass(frozen=True)
class NotificationMyselfResponse:
    id: int
    name: str
    introduction: str
