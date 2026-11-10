"""가족 묶음 줄(같은 보호자·같은 시작 시각·같은 종류의 한 통)의 아이 빼기·더하기(설계 2026-11-10 3.1).

줄의 variables 에 두 칸이 있다 — `pet_ids`("101,102", `#{대상}` 에 실릴 아이들)와 `pet_visits`("101:7,102:8", 아이별
방문 ID). 줄이 달린 아이가 빠지면 `pet_visits` 로 남은 아이의 방문을 찾아 줄을 옮긴다. notification 은 방문 표를 모르므로
짝은 방문마다 오는 이벤트가 채운다. 짝이 없는 아이(이 칸이 생기기 전 줄)에게는 옮기지 못한다.
"""
from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass

from notification.domain.entities.notification_message import NotificationMessage

PET_IDS, PET_VISITS = "pet_ids", "pet_visits"


def pet_ids_of(variables: Mapping[str, str], pet_id: int | None) -> list[int]:
    """variables 의 pet_ids. 그 칸이 없으면(옛 줄) [pet_id], pet_id 도 없으면 []."""
    listed = variables.get(PET_IDS)
    if listed is None:
        return [pet_id] if pet_id is not None else []
    return [int(p) for p in listed.split(",") if p]


def pet_visits_of(variables: Mapping[str, str]) -> dict[int, int]:
    """ "101:7,102:8" → {101: 7, 102: 8}. 칸이 없거나 비면 {}."""
    pairs = (pair.split(":") for pair in variables.get(PET_VISITS, "").split(",") if pair)
    return {int(pet): int(visit) for pet, visit in pairs}


def _written(variables: Mapping[str, str], pet_ids: Collection[int], visits: Mapping[int, int]) -> dict[str, str]:
    return {
        **variables,
        PET_IDS: ",".join(str(p) for p in sorted(pet_ids)),
        PET_VISITS: ",".join(f"{p}:{visits[p]}" for p in sorted(visits)),
    }


@dataclass(frozen=True)
class GroupEdit:
    variables: dict[str, str]   # 고친 variables (다른 칸은 그대로)
    visit_id: int               # 줄이 달릴 방문
    pet_id: int | None
    emptied: bool               # 남는 아이가 없다 — 취소할 줄
    stranded: bool              # 줄이 달린 아이가 빠졌는데 옮길 방문을 모른다


def without_pets(message: NotificationMessage, leaving: Collection[int]) -> GroupEdit | None:
    """leaving 의 아이를 뺀다. 줄의 아이와 겹치지 않으면 None."""
    current = pet_ids_of(message.variables, message.pet_id)
    remaining = [p for p in current if p not in leaving]
    if len(remaining) == len(current):
        return None
    if not remaining:
        return GroupEdit(dict(message.variables), message.visit_id, message.pet_id, emptied=True, stranded=False)
    visits = {p: v for p, v in pet_visits_of(message.variables).items() if p in remaining}
    variables = _written(message.variables, remaining, visits)
    if message.pet_id not in leaving:
        return GroupEdit(variables, message.visit_id, message.pet_id, emptied=False, stranded=False)
    if not visits:
        return GroupEdit(variables, message.visit_id, message.pet_id, emptied=False, stranded=True)
    host = min(visits)
    return GroupEdit(variables, visits[host], host, emptied=False, stranded=False)


def with_pets(
    message: NotificationMessage, pet_ids: Collection[int], pet_id: int | None, visit_id: int
) -> dict[str, str] | None:
    """pet_ids 를 더하고(오름차순·중복 없음) pet_id 가 있으면 pet_visits 에 pet_id:visit_id 를 채운다. 바뀐 것이 없으면 None."""
    current = pet_ids_of(message.variables, message.pet_id)
    visits = pet_visits_of(message.variables)
    if pet_id is not None:
        visits[pet_id] = visit_id
    variables = _written(message.variables, set(current) | set(pet_ids), visits)
    return None if variables == dict(message.variables) else variables
